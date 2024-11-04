import math
from scipy.linalg import block_diag
from typing import Literal

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit import qasm3
from qiskit.circuit.library import XGate
from qiskit.quantum_info import Operator

QASM_OUT_DIR = "qasm"


def big_endian(op: Operator) -> Operator:
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


def export(name: str):
    def decorator(func):
        def wrapper(export: bool = False, *args, **kwargs):
            qc = func(*args, **kwargs)
            if export:
                with open(f"{QASM_OUT_DIR}/{name}.qasm", "w") as f:
                    qasm3.dump(qc, f)
            return qc
        return wrapper
    return decorator


@export("example_1")
def example_1() -> QuantumCircuit:

    qr = QuantumRegister(3, 'q')
    ar = AncillaRegister(1, 'r')
    cr = ClassicalRegister(1, 'c')

    qc = QuantumCircuit(qr, ar, cr)
    qc.h(qr[:])
    
    qc.measure(0, cr)
    with qc.switch(cr) as case:
        with case(0):
            qc.cx(qr[2], ar)
        with case(1):
            qc.reset([0,1])
    
    with qc.while_loop((cr, 1)):
        qc.h(0)
        qc.cx(0, 2)
        qc.measure(2, cr)
    
    return qc


@export("quantum_walk")
def quantum_walk(n: int) -> QuantumCircuit:

    m = math.ceil(math.log2(n)) # number of qubits to encode n positions

    # modulo n increment/decrement operation
    def mod_op(op: Literal["add", "sub"]):
        qr = QuantumRegister(m)
        qc = QuantumCircuit(qr, name=f"mod_{op}")
        for i in range(m - 1, 0, -1):
            ctrl = 2**i - 1 if op == "add" else 0
            qc.append(XGate().control(i, ctrl_state=ctrl), qr[:i + 1])
        qc.x(0)
        return qc
    
    shift = QuantumCircuit(1 + m, name="shift")
    shift.compose(mod_op("sub").control(ctrl_state=0), inplace=True)
    shift.compose(mod_op("add").control(ctrl_state=1), inplace=True)
    shift = shift.to_gate()

    dir = QuantumRegister(1, 'dir') # coin (direction) space
    pos = QuantumRegister(m, 'pos') # position space
    out = ClassicalRegister(m, 'out') # for measurements

    qc = QuantumCircuit(dir, pos, out)
    qc.measure(pos, out)
    with qc.while_loop((out, 0)):
        qc.h(dir)
        qc.compose(shift, inplace=True)
        qc.measure(pos, out)
    
    return qc
