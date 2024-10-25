from typing import Iterator, Optional, Self

from qiskit.quantum_info import Operator
from qiskit.quantum_info.operators.predicates import *
from rustworkx import PyDiGraph

from lib.ops import *
from lib.utils import get_basis, get_statevec, outer
from superop import SuperOperator


class SVTS:
    Qsize: int = -1 # number of quantum variables in global system
    
    cfg: PyDiGraph  # control-flow graph of the SVTS
    init: int       # initial location of the SVTS
    exit: int       # exit location of the SVTS

    def __init__(self):
        """
        Initialise a super-operator-valued transition system.
        """
        if SVTS.Qsize == -1:
            raise RuntimeError("Qsize has not been set")
        
        self.cfg = PyDiGraph(multigraph=False)
        self.init = self.cfg.add_node(None)
        self.exit = self.cfg.add_node(None)

    @classmethod
    def Skip(cls, qvars: Optional[list[int]] = None) -> Self:
        """
        Factory method for SVTS induced by the skip transition rule.

        params:
        - `qvars` (list[int] | None): Quantum variables the program acts on.
        This must be a subset of {0, 1, ..., qsize - 1}. If None is given, the
        program is assumed to act on all quantum variables.

        returns:
        - SVTS of resulting program
        """
        if qvars is None:
            qvars = list(range(cls.Qsize))
        
        ts = cls()
        ts.cfg.add_edge(ts.init, ts.exit, SuperOperator(I, qvars))
        
        return ts
    
    @classmethod
    def Init(cls, qvars: Optional[list[int]] = None) -> Self:
        """
        Factory method for SVTS induced by the initiation transition rule.

        params:
        - `qsize` (int): Number of quantum variables in the system.
        - `qvars` (list[int] | None): Quantum variables the program acts on.
        This must be a subset of {0, 1, ..., qsize - 1}. If None is given, the
        program is assumed to act on all quantum variables.

        returns:
        - SVTS of resulting program
        """
        if qvars is None:
            qvars = list(range(cls.Qsize))

        ts = cls()
        sv_0 = get_statevec((qv_dim := 2 ** len(qvars)), 0) # zero state vector
        ops = [outer(sv_0, bv) for bv in get_basis(qv_dim)]
        ts.cfg.add_edge(ts.init, ts.exit, SuperOperator(ops, qvars))
        
        return ts
    
    @classmethod
    def Unit(cls, op: Operator, qvars: Optional[list[int]] = None) -> Self:
        """
        Factory method for SVTS induced by the unitary transformation
        transition rule.
        
        params:
        - `qsize` (int): Number of quantum variables in the system.
        - `op` (Operator): unitary operator to be applied.
        - `qvars` (list[int] | None): Quantum variables the program acts on.
        This must be a subset of {0, 1, ..., qsize - 1}. If None is given, the
        program is assumed to act on all quantum variables.

        returns:
        - SVTS of resulting program
        """
        if not op.is_unitary():
            raise ValueError("op is not unitary")
        if qvars is None:
            qvars = list(range(cls.Qsize))
        
        ts = cls()
        ts.cfg.add_edge(ts.init, ts.exit, SuperOperator(op, qvars))

        return ts

    @classmethod
    def Comp(cls, l_ts: Self, r_ts: Self) -> Self:
        """
        Factory method for SVTS induced by the sequential composition
        transition rule.

        params:
        - l_ts (SVTS): left program
        - r_ts (SVTS): right program

        returns:
        - SVTS of resulting program
        """
        # initialise composite program as left program
        ts = cls()
        ts.cfg = l_ts.cfg.copy()
        ts.init = l_ts.init

        # merge composite program's exit location with right program's init location
        edge_map_fn = lambda *_: r_ts.init
        new_id = ts.cfg.substitute_node_with_subgraph(l_ts.exit, r_ts.cfg, edge_map_fn)
        
        # update exit location of composite program
        ts.exit = new_id[r_ts.exit]

        return ts

    @classmethod
    def Case(
        cls,
        *cases: tuple[Operator, Self],
        qvars: Optional[list[int]] = None
    ) -> Self:
        """
        Factory method for SVTS induced by the quantum case statement
        transition rule.

        params:
        - `qsize` (int): Number of quantum variables in the system.
        - `cases` (tuple[Operator, SVTS]): Sequence of (M_k, P_k) pairs,
        where M_k is a measurement operator and P_k is the corresponding
        sub-program. Measurement operators must satisfy the completeness
        condition: M_1'M_1 + ... + M_n'M_n = I.
        - `qvars` (list[int] | None): Quantum variables the measurement is
        performed on. This must be a subset of {0, 1, ..., qsize - 1}. If
        None is given, the measurement is assumed to be performed on all
        quantum variables.
        """
        if qvars is None:
            qvars = list(range(cls.Qsize))
        
        if len(set(m_op.dim for m_op, _ in cases)) > 1:
            raise ValueError("measurement operators have different dimensions")
        if not is_identity_matrix(sum(m_op for m_op, _ in cases)):
            raise ValueError("completeness condition is not satisfied")
        
        ts = cls()
        sub_exits = []

        # connect init location to sub-programs
        for m_op, s_ts in cases:
            node_map = {ts.init: (s_ts.init, SuperOperator(m_op, qvars))}
            new_id = ts.cfg.compose(s_ts.cfg, node_map)
            sub_exits.append(new_id[s_ts.exit])
        
        # merge all exit locations
        ts.exit = ts.cfg.contract_nodes(sub_exits + [ts.exit], None)
        
        return ts

    @classmethod
    def Loop(cls,
        t_op: Operator,
        f_op: Operator,
        s_ts: Self,
        qvars: Optional[list[int]] = None
    ) -> Self:
        """
        params:
        - `qsize` (int): Number of quantum variables in the system.
        - `t_op` (Operator): Measurement operator representing true condition.
        - `f_op` (Operator): Measurement operator representing false condition.
        - `s_ts` (SVTS): Sub-program in the body of the loop. 
        - `qvars` (list[int] | None): Quantum variables the measurement is
        performed on. This must be a subset of {0, 1, ..., qsize - 1}. If
        None is given, the measurement is assumed to be performed on all
        quantum variables.
        """
        if qvars is None:
            qvars = list(range(cls.Qsize))
        
        if t_op.dim != f_op.dim:
            raise ValueError("measurement operators have different dimensions")
        if not is_identity_matrix(t_op + f_op):
            raise ValueError("completeness condition is not satisfied")
        
        ts = cls()

        # connect init location (loop condition) to exit location (when false)
        ts.cfg.add_edge(ts.init, ts.exit, SuperOperator(f_op, qvars))

        # connect init location (loop condition) to sub-program (when true)
        node_map = {ts.init: (s_ts.init, SuperOperator(t_op, qvars))}
        new_id = ts.cfg.compose(s_ts.cfg, node_map)

        # merge exit location of subprogram with init location
        ts.init = ts.cfg.contract_nodes([new_id[s_ts.exit], ts.init], None)

        return ts

    def transitions(self) -> Iterator[tuple[int, int, SuperOperator]]:
        """
        Return an iterator over the transitions in this SVTS. Each
        transition is a tuple of the form (pre, post, s_op).

        returns:
        - Iterator over sequence of (pre, post, s_op).
        """
        edges = sorted(self.cfg.edge_list())
        for pre, post in edges:
            yield pre, post, self.cfg.get_edge_data(pre, post)
    

if __name__ == "__main__":

    SVTS.Qsize = 3

    # case statement
    ts_0 = SVTS.Unit(Operator(CX), qvars=[2,1])
    ts_1 = SVTS.Init(qvars=[1,2])
    l_ts = SVTS.Case((M0, ts_0), (M1, ts_1), qvars=[0])

    # while loop
    s_ts = SVTS.Unit(H.tensor(H), qvars=[1,0])
    r_ts = SVTS.Loop(M0, M1, s_ts, qvars=[2])

    ts = SVTS.Comp(l_ts, r_ts)

    print(f"init: {ts.init}")
    print(f"exit: {ts.exit}")
    for pre, post, s_op in ts.transitions():
        print(f"{pre} -> {post}: {s_op}")
