import math

import qiskit.circuit.library as lib
from qiskit.quantum_info import Operator


def _big_endian(op: Operator) -> Operator:
    """
    Convert an operator from little endian to an equivalent operator in big endian.

    :param Operator op: Operator written in little endian.

    :return: Equivalent operator written in big endian.
    :rtype: Operator
    """
    qsize = int(math.log2(op.dim[0]))
    qargs = list(reversed(range(qsize)))
    op = op.apply_permutation(qargs, front=True)
    op = op.apply_permutation(qargs)
    return op

GATE = {
     "I": Operator.from_label('I'),
     "X": Operator.from_label('X'),
     "Y": Operator.from_label('Y'),
     "Z": Operator.from_label('Z'),
     "H": Operator.from_label('H'),
    "CX": _big_endian(Operator(lib.CXGate())),
    "CY": _big_endian(Operator(lib.CYGate())),
    "CZ": _big_endian(Operator(lib.CZGate())),
    "M0": Operator.from_label('0'),
    "M1": Operator.from_label('1'),
}
