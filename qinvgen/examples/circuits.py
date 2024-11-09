import math
from scipy.linalg import block_diag
from typing import Literal

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit import qasm3
from qiskit.circuit.library import XGate

QASM_OUT_DIR = "qasm"


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
    """
    Example circuit 1.
    """
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


def qwalk(n: int) -> QuantumCircuit:
    """
    Quantum walk circuit.
    """
    m = math.ceil(math.log2(n)) # number of qubits to encode n positions

    # modulo n increment/decrement operation
    def shift_op(op: Literal['l', 'r']):
        qr = QuantumRegister(m)
        qc = QuantumCircuit(qr, name=f"{op}shift")
        for i in range(m - 1, 0, -1):
            ctrl = 2**i - 1 if op == 'r' else 0
            qc.append(XGate().control(i, ctrl_state=ctrl), qr[:i + 1])
        qc.x(0)
        return qc.reverse_bits()

    dir = QuantumRegister(1, 'dir') # coin (direction) space
    pos = QuantumRegister(m, 'pos') # position space
    out = ClassicalRegister(m, 'out') # for measurements

    qc = QuantumCircuit(dir, pos, out)
    qc.measure(pos, out)
    with qc.while_loop((out, 0)):
        qc.h(dir)
        qc.x(dir)
        qc.compose(shift_op('l').control(), inplace=True)
        qc.x(dir)
        qc.compose(shift_op('r').control(), inplace=True)
        qc.measure(pos, out)
    
    return qc


@export("qwalk_2")
def qwalk_2() -> QuantumCircuit:
    """
    Quantum walk circuit with 2 position qubits.
    """
    return qwalk(n=4)


@export("qwalk_3")
def qwalk_3() -> QuantumCircuit:
    """
    Quantum walk circuit with 3 position qubits.
    """
    return qwalk(n=8)
