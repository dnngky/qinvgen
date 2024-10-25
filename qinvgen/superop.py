import numpy as np
from qiskit.quantum_info import Kraus, Operator

from lib.ops import *


class SuperOperator(Kraus):
    """
    Kraus representation of a Super-operator.
    """
    _qvars: list[int]   # ordered quantum variables applied on by super-operator
    _qvdim: int         # dimension of state space induced by quantum variables

    def __init__(self, data: Operator | list[Operator], qvars: list[int]):
        """
        Initialise a super-operator.
        """
        self._qvars = qvars
        self._qvdim = 2 ** len(qvars)
        super().__init__(data)

        if len(set(self._qvars)) < len(self._qvars):
            raise ValueError(f"qvars contain duplicate qubits")
        if self.dim[0] != self._qvdim:
            raise ValueError(
                f"mismatch between dim of super-op ({self.dim[0]}) and qvars ({self._qvdim})"
            )

    def __repr__(self) -> str:
        data = np.array_str(sum(self._data[0])).replace('\n', '\n  ')
        qvars = ','.join(map(str, self._qvars))
        return f"SuperOperator(\n  {''.join(data)}\n  qvars=[{qvars}]\n)"
