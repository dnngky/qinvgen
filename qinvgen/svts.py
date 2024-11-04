from contextlib import contextmanager
from typing import Iterator, Optional, Self

from qiskit.quantum_info import Operator
from qiskit.quantum_info.operators.predicates import *
from rustworkx import PyDiGraph

from lib.gates import *
from lib.utils import *
from superop import SuperOperator


class SVTSMeta(type):
    _qsize: int # global quantum variables

    def __init__(cls, *args, **kwargs):
        cls._qsize = -1

    @property
    def qsize(cls) -> int:
        return cls._qsize

    @property
    def qvars(cls) -> list[int]:
        return list(range(cls._qsize))
    
    @qsize.setter
    def qsize(cls, _):
        raise AttributeError("qsize is a read-only attribute")
    
    @qvars.setter
    def qvars(cls, _):
        raise AttributeError("qvars is a read-only attribute")
    
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
            cls._qsize = -1 # reset qvars before exiting


class SVTS(metaclass=SVTSMeta):
    """
    Super-operator-Valued Transition System.
    """
    cfg: PyDiGraph  # control-flow graph
    lin: int        # in location
    lout: int       # out location

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
        if not SVTS.qvars:
            raise RuntimeError("SVTS must be instantiated under meta_init")
        
        self.cfg = PyDiGraph(multigraph=False)
        self.lin = self.cfg.add_node(None)
        self.lout = self.cfg.add_node(None)

    @classmethod
    def skip(cls) -> Self:
        """
        Factory method for SVTS induced by the skip transition rule.

        :return: Resulting program.
        :rtype: SVTS
        """
        ts = cls()
        ts.cfg.add_edge(ts.lin, ts.lout, SuperOperator(GATE["I"], cls.qvars))
        
        return ts
    
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
        
        ts = cls()
        sv_0 = get_statevec(len(qargs), 0) # zero state vector
        op = [outer(sv_0, bv) for bv in get_basis(len(qargs))]
        ts.cfg.add_edge(ts.lin, ts.lout, SuperOperator(op, qargs))
        
        return ts
    
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
            raise ValueError("op is not unitary")
        
        main = cls()
        main.cfg.add_edge(main.lin, main.lout, SuperOperator(op, qargs))

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
        main.cfg = left.cfg.copy()
        main.lin = left.lin

        # merge left program's lout with right program's lin
        edge_map_fn = lambda *_: right.lin
        new_id = main.cfg.substitute_node_with_subgraph(left.lout, right.cfg, edge_map_fn)
        
        # update lout of main
        main.lout = new_id[right.lout]

        return main

    @classmethod
    def case(
        cls,
        *cases: tuple[Operator, Self],
        qargs: Optional[list[int]] = None
    ) -> Self:
        """
        Factory method for SVTS induced by the quantum case statement
        transition rule.

        :param tuple[Operator, SVTS] *cases: Sequence of (M_k, P_k) pairs,
        where M_k is a measurement operator and P_k is the corresponding
        sub-program. Measurement operators must satisfy the completeness
        condition: M_1'M_1 + ... + M_n'M_n = I.
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
        if len(set(m_op.dim for m_op, _ in cases)) > 1:
            raise ValueError("measurement operators have different dimensions")
        if not is_identity_matrix(sum(m_op.adjoint() @ m_op for m_op, _ in cases)):
            raise ValueError("completeness condition is not satisfied")
        
        main = cls()

        # connect main's lin to sub-programs' lin
        sub_exits = []
        for op, sub in cases:
            node_map = {main.lin: (sub.lin, SuperOperator(op, qargs))}
            new_id = main.cfg.compose(sub.cfg, node_map)
            sub_exits.append(new_id[sub.lout])
        
        # merge all louts
        main.lout = main.cfg.contract_nodes(sub_exits + [main.lout], None)
        
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
        if true.dim != false.dim:
            raise ValueError("measurement operators have different dimensions")
        if not is_identity_matrix(true + false):
            raise ValueError("completeness condition is not satisfied")
        
        ts = cls()

        # connect main's lin (loop condition) to its lout (when false)
        ts.cfg.add_edge(ts.lin, ts.lout, SuperOperator(false, qargs))

        # connect main's lin (loop condition) to sub-program's lin (when true)
        node_map = {ts.lin: (body.lin, SuperOperator(true, qargs))}
        new_id = ts.cfg.compose(body.cfg, node_map)

        # merge sub-programs' lout with main's lin
        ts.lin = ts.cfg.contract_nodes([new_id[body.lout], ts.lin], None)

        return ts

    def transitions(self) -> Iterator[tuple[int, int, SuperOperator]]:
        """
        Return an iterator over the transitions in this SVTS. Each
        transition is a tuple of the form (pre, post, op).

        :return: Iterator over sequence of (pre, post, op).
        :rtype: Iterator[tuple[int, int, SuperOperator]]
        """
        edges = sorted(self.cfg.edge_list())
        for pre, post in edges:
            yield pre, post, self.cfg.get_edge_data(pre, post)
    

if __name__ == "__main__":

    with SVTS.meta_init(qvars=3):

        # case statement
        ts_0 = SVTS.unit(Operator(GATE["CX"]), qargs=[2,1])
        ts_1 = SVTS.init(qargs=[1,2])
        l_ts = SVTS.case((GATE["M0"], ts_0), (GATE["M1"], ts_1), qargs=[0])

        # while loop
        s_ts = SVTS.unit(GATE["H"].tensor(GATE["H"]), qargs=[1,0])
        r_ts = SVTS.loop(GATE["M0"], GATE["M1"], s_ts, qargs=[2])

        ts = SVTS.comp(l_ts, r_ts)

    print(f"init: {ts.lin}")
    print(f"exit: {ts.lout}")
    for pre, post, s_op in ts.transitions():
        print(f"{pre} -> {post}: {s_op}")
