import qiskit.circuit.library as lib
from qiskit.quantum_info import Operator

""" SINGLE-QUBIT GATES """
I = Operator.from_label('I')
X = Operator.from_label('X')
Y = Operator.from_label('Y')
Z = Operator.from_label('Z')
H = Operator.from_label('H')

""" DOUBLE-QUBIT GATES """
CX = Operator(lib.CXGate())
CY = Operator(lib.CYGate())
CZ = Operator(lib.CZGate())

""" MEASUREMENTS """
M0 = Operator.from_label('0')
M1 = Operator.from_label('1')

""" BELL STATES """
B0 = Operator.from_label('+')
B1 = Operator.from_label('-')
