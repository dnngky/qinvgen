import numpy as np
import rustworkx as rx
import scipy.sparse as sp

from qiskit.circuit.library import IGate


def expand(op: np.ndarray, num_qubits: int) -> np.ndarray:
    """
    Expand `op` to a system comprising `num_qubits` qubits.
    """
    if num_qubits == 1:
        return op
    for _ in range(num_qubits - 1):
        op = np.kron(op, IGate())
    return op

class SVTS:
    n_qubits: int
    cfg: rx.PyDiGraph # control-flow graph

    def __init__(self, n_qubits: int):
        self.n_qubits = n_qubits
        self.cfg = rx.PyDiGraph(multigraph=False)
        self.lin = self.cfg.add_node("lin")
        self.lout = self.cfg.add_node("lout")
        id_gate = sp.coo_matrix((
            [1.+0j] * (n_qubits ** 2), # data
            (list(range(n_qubits ** 2)),) * 2 # (i, j)
        ))
        self.cfg.add_edge(self.lin, self.lout, id_gate.toarray())


if __name__ == "__main__":

    ts = SVTS(4)
    print(ts.cfg.edges())