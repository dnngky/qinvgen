from contextlib import contextmanager
from typing import Iterator, Optional, Self

from qiskit.quantum_info import Kraus, Operator
from qiskit.quantum_info.operators.predicates import is_identity_matrix
from rustworkx import PyDiGraph

from lib.stdops import FIXEDGATE
from lib.utils import *


class SVTSMeta(type):
    _qsize: int # global quantum variables

    def __init__(cls, *args, **kwargs):
        cls._qsize = 0

    @property
    def qsize(cls) -> int:
        return cls._qsize

    @property
    def qvars(cls) -> list[int]:
        return list(range(cls._qsize))
    
    @contextmanager
    def meta_init(cls, qsize: int):
        """
        Instantiate a SVTS and set the set of global quantum variables.

        :param int qvars: Global quantum variables, indexed {0, 1, ..., qvars - 1}.

        :return: Context manager for the instantiated SVTS.
        :rtype: ContextManager
        """
        cls._qsize = qsize # bypass read-only guard
        try:
            yield
        finally:
            cls._qsize = 0 # reset qvars before exiting


class SVTS(metaclass=SVTSMeta):
    """
    Super-operator-Valued Transition System.
    """
    _qsize: int      # number of quantum variables
    _cfg: PyDiGraph  # control-flow graph
    _lin: int        # in location
    _lout: int       # out location

    def __init__(self):
        """
        Initialise an SVTS. Instantiation is only permitted to occur under the
        context manager `meta_init`, which sets the global `qvars`:

        An example is as follows:
        ```
        with SVTS.meta_init(qvars=3):
            SVTS.init([1, 2])
            SVTS.unit('H', [0])
        ```
        """
        if not SVTS.qsize:
            raise RuntimeError("SVTS must be instantiated under meta_init")
        
        self._qsize = SVTS.qsize
        self._cfg = PyDiGraph(multigraph=False)
        self._lin = self._cfg.add_node(None)
        self._lout = self._cfg.add_node(None)

    @property
    def qsize(self) -> int:
        """
        Number of quantum variables in the program.
        """
        return self._qsize
    
    @property
    def qvars(self) -> list[int]:
        """
        Quantum variables used in the program.
        """
        return list(range(self._qsize))
    
    @property
    def cfg(self) -> PyDiGraph:
        """
        Control-flow graph representing the program.
        """
        return self._cfg.copy()
    
    @property
    def locations(self) -> list[int]:
        """
        Locations in the program.
        """
        return list(self._cfg.node_indices())
    
    @property
    def lin(self) -> int:
        """
        Init location of the program.
        """
        return self._lin
    
    @property
    def lout(self) -> int:
        """
        Exit location of the program.
        """
        return self._lout

    @classmethod
    def skip(cls) -> Self:
        """
        Factory method for SVTS induced by the skip transition rule.

        :return: Resulting program.
        :rtype: SVTS
        """
        main = cls()
        s_op = Kraus(FIXEDGATE["I"])
        main._cfg.add_edge(main._lin, main._lout, (s_op, [0]))
        
        return main
    
    @classmethod
    def init(cls, qargs: Optional[list[int]] = None) -> Self:
        """
        Factory method for SVTS induced by the initiation transition rule.

        :param list[int] | None qargs: Quantum variables the program acts
            on. This must be a subset of `cls.qvars`. If None is given,
            the program is assumed to act on all of `cls.qvars`.

        :return: Resulting program.
        :rtype: SVTS
        """
        qargs = cls.qvars if qargs is None else qargs

        if len(qset := set(qargs)) != len(qargs):
            raise ValueError("qargs contain duplicate qubits")
        if qset - set(cls.qvars):
            raise ValueError("qargs is not a subset of qvars")
        
        main = cls()
        dims = (2,) * len(qargs)
        zero = Statevector.from_int(0, dims)
        s_op = [outer(Statevector.from_int(i, dims), zero) for i in range(2 ** len(qargs))]
        main._cfg.add_edge(main._lin, main._lout, (Kraus(s_op), qargs))
        
        return main
    
    @classmethod
    def unit(cls, op: Operator, qargs: Optional[list[int]] = None) -> Self:
        """
        Factory method for SVTS induced by the unitary transformation
        transition rule.
        
        :param Operator op: Unitary operator to be applied.
        :param list[int] | None qargs: Quantum variables the program acts
            on. This must be a subset of `cls.qvars`. If None is given,
            the program is assumed to act on all of `cls.qvars`.

        :return: Resulting program.
        :rtype: SVTS
        """
        qargs = cls.qvars if qargs is None else qargs

        if len(qset := set(qargs)) != len(qargs):
            raise ValueError("qargs contain duplicate qubits")
        if qset - set(cls.qvars):
            raise ValueError("qargs is not a subset of qvars")
        if not op.is_unitary():
            raise ValueError(f"op {op} is not unitary")
        
        main = cls()
        main._cfg.add_edge(main._lin, main._lout, (Kraus(op), qargs))

        return main

    @classmethod
    def comp(cls, left: Self, right: Self) -> Self:
        """
        Factory method for SVTS induced by the sequential composition
        transition rule.

        :param SVTS left: Left program.
        :param SVTS right: Right program.

        :return: Resulting program.
        :rtype: SVTS
        """
        # initialise main as left program
        main = cls()
        main._cfg = left._cfg.copy()
        main._lin = left._lin

        # merge left program's lout with right program's lin
        edge_map_fn = lambda *_: right._lin
        new_id = main._cfg.substitute_node_with_subgraph(left._lout, right._cfg, edge_map_fn)
        
        # update lout of main
        main._lout = new_id[right._lout]

        return main

    @classmethod
    def case(
        cls,
        *cases: tuple[Operator, Self],
        qargs: Optional[list[int]] = None,
    ) -> Self:
        """
        Factory method for SVTS induced by the quantum case statement
        transition rule.

        :param tuple[Operator, SVTS] *cases: Sequence of (M_k, P_k) pairs, where
            M_k is a measurement operator and P_k is the corresponding sub-program.
            Measurement operators must satisfy the completeness condition
            M_1'M_1 + ... + M_n'M_n = I.
        :param SVTS | None default: The sub-program corresponding to the default case.
            If None is given, a trivial program (skip) is assumed.
        :param list[int] | None qargs: Quantum variables measured in the condition.
            This must be a subset of `cls.qvars`. If None is given, the measurement
            is assumed to be performed on all of `cls.qvars`.

        :return: Resulting program.
        :rtype: SVTS
        """
        qargs = cls.qvars if qargs is None else qargs

        if len(qset := set(qargs)) != len(qargs):
            raise ValueError("qargs contain duplicate qubits")
        if qset - set(cls.qvars):
            raise ValueError("qargs is not a subset of qvars")
        if len(set(m_op.dim for m_op, _ in cases)) > 1:
            raise ValueError("measurement operators have different dimensions")
        if not is_identity_matrix(sum(m_op.adjoint() @ m_op for m_op, _ in cases)):
            raise ValueError("completeness condition is not satisfied")
        
        main = cls()

        # connect main's lin to sub-programs' lin
        sub_exits = []
        for m_op, sub in cases:
            node_map = {main._lin: (sub._lin, (Kraus(m_op), qargs))}
            new_id = main._cfg.compose(sub._cfg, node_map)
            sub_exits.append(new_id[sub._lout])
        
        # merge all louts
        main._lout = main._cfg.contract_nodes(sub_exits + [main._lout], None)
        
        return main

    @classmethod
    def loop(cls,
        true: Operator,
        false: Operator,
        body: Self,
        qargs: Optional[list[int]] = None
    ) -> Self:
        """
        Factory method for SVTS induced by the quantum loop transition rule.

        :param Operator true: Measurement operator representing true condition.
        :param Operator false: Measurement operator representing false condition.
        :param SVTS body: Sub-program in the body of the loop. 
        :param list[int] | None qargs: Quantum variables measured in the condition.
            This must be a subset of `cls.qvars`. If None is given, the measurement
            is assumed to be performed on all of `cls.qvars`.

        :return: Resulting program.
        :rtype: SVTS
        """
        qargs = cls.qvars if qargs is None else qargs

        if len(qset := set(qargs)) != len(qargs):
            raise ValueError("qargs contain duplicate qubits")
        if qset - set(cls.qvars):
            raise ValueError("qargs is not a subset of qvars")
        if true.dim != false.dim:
            raise ValueError("measurement operators have different dimensions")
        if not is_identity_matrix(true + false):
            raise ValueError("completeness condition is not satisfied")
        
        ts = cls()

        # connect main's lin (loop condition) to its lout (when false)
        ts._cfg.add_edge(ts._lin, ts._lout, (Kraus(false), qargs))

        # connect main's lin (loop condition) to sub-program's lin (when true)
        node_map = {ts._lin: (body._lin, (Kraus(true), qargs))}
        new_id = ts._cfg.compose(body._cfg, node_map)

        # merge sub-programs' lout with main's lin
        ts._lin = ts._cfg.contract_nodes([new_id[body._lout], ts._lin], None)

        return ts

    def transitions(self) -> Iterator[tuple[int, int, tuple[Kraus, list[int]]]]:
        """
        Return an iterator over the transitions in this SVTS. Each
        transition is a tuple of the form (pre, post, (op, qargs)).

        :return: Iterator over transitions.
        :rtype: Iterator[tuple[int, int, Kraus]]
        """
        edges = sorted(self._cfg.edge_list())
        for pre, post in edges:
            yield pre, post, self._cfg.get_edge_data(pre, post)

    def minimise(self, head: Optional[int] = None) -> None:
        """
        Simplify the SVTS by contracting cutpoint-free paths.

        :param int head: The location to start reducing from. If None is given,
        this is set to the initial location.
        """
        ss_op = Kraus(np.identity(2 ** self.qsize)) # compound op
        locs = [] # locations to be contracted
        head = self._lin if head is None else head
        
        loc = head
        while self._cfg.in_degree(loc) <= self._cfg.out_degree(loc) == 1:
            _, loc, (s_op, qargs) = self._cfg.out_edges(loc)[0]
            if not is_identity_matrix(s_op):
                s_op = expand(s_op, self.qsize, qargs)
                ss_op &= s_op
            locs.append(loc)
        
        if len(locs) <= 1:
            return
        
        tail = self._cfg.contract_nodes(locs, None) # contract path into single transition
        self._cfg.update_edge(head, tail, (ss_op, self.qvars)) # set op for transition

        if locs[-1] == self._lout:
            self._lout = tail # update exit location if needed
        
        for loc in self._cfg.successor_indices(tail):
            self.minimise(loc) # reduce other paths, if any

    def add_outloop(self) -> None:
        """
        Add an identity self-loop transition to the exit location.
        """
        s_op = Kraus(FIXEDGATE["I"])
        self._cfg.add_edge(self._lout, self._lout, (s_op, [0]))


if __name__ == "__main__":

    with SVTS.meta_init(qsize=3):

        # case statement
        ts_0 = SVTS.unit(FIXEDGATE["CX"], qargs=[2,1])
        ts_1 = SVTS.init(qargs=[1,2])
        l_ts = SVTS.case((FIXEDGATE["M0"], ts_0), (FIXEDGATE["M1"], ts_1), qargs=[0])

        # while loop
        s_ts = SVTS.unit(FIXEDGATE["H"].tensor(FIXEDGATE["H"]), qargs=[1,0])
        r_ts = SVTS.loop(FIXEDGATE["M0"], FIXEDGATE["M1"], s_ts, qargs=[2])

        ts = SVTS.comp(l_ts, r_ts)

    print(f"init: {ts._lin}")
    print(f"exit: {ts._lout}")
    for pre, post, (s_op, qargs) in ts.transitions():
        print(f"{pre} -> {post}: {s_op.data}")
    