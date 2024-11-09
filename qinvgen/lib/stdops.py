import math

import qiskit.circuit.library as lib
from qiskit.quantum_info import Operator


def _flip_endian(op: Operator) -> Operator:
    """
    Convert an operator written in little (resp. big) endian to an equivalent
    operator written in big (resp. little) endian.

    :param Operator op: Operator written in little endian.

    :return: Equivalent operator written in big endian.
    :rtype: Operator
    """
    qsize = int(math.log2(op.dim[0]))
    qargs = list(reversed(range(qsize)))
    op = op.apply_permutation(qargs, front=True)
    op = op.apply_permutation(qargs)
    return op


# Constants
CONST = {
    "PI": math.pi
}

# Unary operation
UNROP = {
    "-": lambda val: -val
}

# Binary operations
BINOP = {
    "+": lambda lhs, rhs: lhs + rhs,
    "-": lambda lhs, rhs: lhs - rhs,
    "*": lambda lhs, rhs: lhs * rhs,
    "/": lambda lhs, rhs: lhs / rhs,
}

# Gates without parameters
FIXEDGATE = {
    "I"  : Operator.from_label('I'),
    "X"  : Operator.from_label('X'),
    "Y"  : Operator.from_label('Y'),
    "Z"  : Operator.from_label('Z'),
    "H"  : Operator.from_label('H'),
    "M0" : Operator.from_label('0'),
    "M1" : Operator.from_label('1'),
    "CX" : _flip_endian(Operator(lib.CXGate())),
    "CY" : _flip_endian(Operator(lib.CYGate())),
    "CZ" : _flip_endian(Operator(lib.CZGate())),
    "CCX": _flip_endian(Operator(lib.CCXGate())),
}

# Gates with parameters
PARAMGATE = {
    "P" : lambda *args: Operator(lib.PhaseGate(*args)),
    "U" : lambda *args: Operator(lib.UGate(*args)),
    "CU": lambda *args: _flip_endian(Operator(lib.CUGate(*args))),
}
