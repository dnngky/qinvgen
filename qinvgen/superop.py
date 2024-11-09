from typing import Self

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
        self._qargs = qargs.copy()

        if len(set(self._qargs)) < len(self._qargs):
            raise ValueError(f"qargs contain duplicate qubits")
        
    @property
    def qargs(self) -> list[int]:
        return self._qargs.copy()
    
    @qargs.setter
    def qargs(self, new_qargs: list[int]):
        self._qargs = new_qargs
        
    def __matmul__(self, other: Self | Operator):
        other_data = other._data
        if isinstance(other, SuperOperator):
            other_data = other_data[0]
        return SuperOperator(Kraus(self._data[0]) @ Kraus(other_data), self._qargs)

    def __and__(self, other: Self | Operator):
        other_data = other._data
        if isinstance(other, SuperOperator):
            other_data = other_data[0]
        return SuperOperator(Kraus(self._data[0]) & Kraus(other_data), self._qargs)
    
    def dot(self, other: Self | Operator):
        return self @ other
    
    def compose(self, other: Self | Operator):
        return self & other

    def __repr__(self) -> str:
        op = np.array_str(sum(self._data[0])).replace('\n', '\n  ')
        qargs = ','.join(map(str, self._qargs))
        return f"SuperOperator(\n  {''.join(op)}\n  qargs=[{qargs}]\n)"
