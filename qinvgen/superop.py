import numpy as np
from qiskit.quantum_info import Kraus, Operator


class SuperOperator(Kraus):
    """
    Kraus representation of a Superoperator.
    """
    _qargs: list[int]   # ordered quantum variables applied on by super-operator

    def __init__(self, op: Operator | list[Operator], qargs: list[int]):
        """
        Initialise a superoperator.
        """
        super().__init__(op)
        self._qargs = qargs

        if len(set(self._qargs)) < len(self._qargs):
            raise ValueError(f"qargs contain duplicate qubits")
        # if self.dim[0] != (qdim := 2 ** len(qargs)):
        #     raise ValueError(
        #         f"mismatch between dim of super-op ({self.dim[0]}) and qargs ({qdim})"
        #     )

    def __repr__(self) -> str:
        op = np.array_str(sum(self._data[0])).replace('\n', '\n  ')
        qargs = ','.join(map(str, self._qargs))
        return f"SuperOperator(\n  {''.join(op)}\n  qargs=[{qargs}]\n)"
