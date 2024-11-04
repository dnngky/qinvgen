from openqasm3.ast import *
from openqasm3.parser import parse

from lib.gates import GATE
from lib.utils import *
from svts import SVTS

from tests.debug import debug
from tests.test_parser import abstract_debug


def _abstract_quantum_gate(stmt: QuantumGate) -> SVTS:

    op = GATE[stmt.name.name.upper()]
    qargs = [
        qvars[qvar.name.name][qind[0].value]
        for qvar in stmt.qubits for qind in qvar.indices
    ]
    return SVTS.unit(op, qargs)


def _abstract_quantum_reset(stmt: QuantumReset) -> SVTS:

    qvar = stmt.qubits
    qind = qvar.indices[0][0]
    qarg = qvars[qvar.name.name][qind.value]
    return SVTS.init(qargs=[qarg])


def _abstract_switch_statement(stmt: SwitchStatement) -> SVTS:

    cases = []
    for head, body in stmt.cases:
        op = outer(get_statevec(qsize=1, val=head[0].value)) # TODO
        sub = abstract(body.statements, qsize, qvars)
        cases.append((op, sub))
    return SVTS.case(*cases, qargs=[0]) # TODO


def _abstract_while_loop(stmt: WhileLoop) -> SVTS:

    cond = stmt.while_condition
    val = cond.rhs.value
    meas = list(map(outer, get_basis(qsize=1))) # TODO
    match cond.op.name:
        case "==":
            true = meas[val]
            false = sum(meas[:val] + meas[val + 1:])
        case "!=":
            true = sum(meas[:val] + meas[val + 1:])
            false = meas[val]
        case "<":
            true = sum(meas[:val])
            false = sum(meas[val:])
        case "<=":
            true = sum(meas[:val + 1])
            false = sum(meas[val + 1:])
        case ">":
            true = sum(meas[val + 1:])
            false = sum(meas[:val + 1])
        case ">=":
            true = sum(meas[val:])
            false = sum(meas[:val])
    body = abstract(stmt.block, qsize, qvars)
    return SVTS.loop(true, false, body, qargs=[0]) # TODO


@debug(abstract_debug)
def abstract(program: list[Statement], qsize: int, qvars: dict[str, list[int]], **kwargs) -> SVTS:
    """
    Perform abstraction of a program into an SVTS.

    :param list[Statement] program: The input program.
    :param int qsize: Total number of quantum variables.
    :param dict[str, list[int]] qvars: A dictionary with quantum registers as keys and the indices
        of its quantum variables as values.
    
    :return: SVTS of the input program.
    :rtype: SVTS
    """
    stmt = program[0]
    ts = None

    match stmt:

        case ClassicalAssignment():
            ts = SVTS.skip()

        case ClassicalDeclaration():
            ts = SVTS.skip()
        
        case QubitDeclaration():
            ts = SVTS.skip()

        case QuantumGate():
            ts = _abstract_quantum_gate(stmt)

        case QuantumMeasurementStatement():
            ts = SVTS.skip()

        case QuantumReset():
            ts = _abstract_quantum_reset(stmt)
        
        case SwitchStatement():
            ts = _abstract_switch_statement(stmt)
        
        case WhileLoop():
            ts = _abstract_while_loop(stmt)
        
        case _:
            ts = SVTS.skip()

    if len(program) > 1:
        ts = SVTS.comp(ts, abstract(program[1:], qsize, qvars))
    
    return ts


def get_qvars(program: list[Statement]) -> dict[str, int]:
    """
    Extract all quantum variables (qubits) from quantum declarations in the program.
    
    :param list[Statement] program: The input program.

    :return: Total number of quantum variables.
    :rtype: int
    :return: A dictionary with quantum registers as keys and the indices of its quantum
    variables as values.
    :rtype: dict[str, list[int]]
    """
    qsize = 0
    qvars = {}

    for stmt in program:
        if not isinstance(stmt, QubitDeclaration):
            continue
        qvars[stmt.qubit.name] = list(range(qsize, (qsize := qsize + stmt.size.value)))
    
    return qsize, qvars


if __name__ == "__main__":

    with open("examples/qasm/quantum_walk.qasm", 'r') as file:
        stream = "".join(file.readlines()).strip()
    
    program = parse(stream).statements
    qsize, qvars = get_qvars(program)

    with SVTS.meta_init(qsize=qsize):
        ts = abstract(program, qsize, qvars)

    if ts:
        print(f"init location: {ts.lin}")
        print(f"exit location: {ts.lout}")
        for pre, post, s_op in ts.transitions():
            print(f"{pre} -> {post}: {s_op}")
