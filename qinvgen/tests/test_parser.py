from typing import *

from openqasm3.ast import *

from svts import SVTS


def _assert_classical_assignment(stmt: ClassicalAssignment, ind: int):

    # only form of classical assignment expected is switch_dummy = c
    assert isinstance(lhs := stmt.lvalue, Identifier)
    assert isinstance(op := stmt.op, AssignmentOperator)
    assert isinstance(rhs := stmt.rvalue, Identifier)
    print(ind * ' ' + f"{lhs.name} {op.name} {rhs.name}")


def _assert_classical_declaration(stmt: ClassicalDeclaration, ind: int):
    
    assert isinstance(datatype := stmt.type, ClassicalType)
    if isinstance(datatype, BitType):
        assert isinstance(size := datatype.size, IntegerLiteral)
        return f"{stmt.identifier.name}: bit[{size.value}]"
    print(ind * ' ' + f"{stmt.identifier.name}: int")


def _assert_qubit_declaration(stmt: QubitDeclaration, ind: int):
    
    assert isinstance(size := stmt.size, IntegerLiteral)
    print(ind * ' ' + f"{stmt.qubit.name} = qubit({size.value})")


def _assert_quantum_gate(stmt: QuantumGate, qvars: dict[str, list[int]], ind: int):
    
    op = stmt.name.name.upper()
    op_qvars = []
    for qvar in stmt.qubits:
        assert isinstance(qvar, IndexedIdentifier)
        assert all(len(qvind) == 1 and isinstance(qvind[0], IntegerLiteral) for qvind in qvar.indices)
        op_qvars.extend([qvars[qvar.name.name][qvind[0].value] for qvind in qvar.indices])
    print(ind * ' ' + f"{op}({','.join(map(lambda s: f"q[{s}]", op_qvars))})")


def _assert_quantum_measurement(stmt: QuantumMeasurementStatement, ind: int):
    
    assert isinstance(qvar := stmt.measure.qubit, IndexedIdentifier)
    assert len(qinds := qvar.indices) == 1 and len(qvind := qinds[0]) == 1 # only measure one qubit at a time
    assert isinstance(qvind := qvind[0], IntegerLiteral)
    assert isinstance(cvar := stmt.target, IndexedIdentifier)
    assert len(cinds := cvar.indices) == 1 and len(cind := cinds[0]) == 1 # only measure to one clbit at a time
    assert isinstance(cind := cind[0], IntegerLiteral)
    print(ind * ' ' + f"{cvar.name.name}[{cind.value}] = measure({qvar.name.name}[{qvind.value}])")


def _assert_quantum_reset(stmt: QuantumReset, qvars: dict[str, list[int]], ind: int):
    
    assert isinstance(qvar := stmt.qubits, IndexedIdentifier)
    assert len(qinds := qvar.indices) == 1 and len(qvind := qinds[0]) == 1 # only reset one qubit at a time
    assert isinstance(qvind := qvind[0], IntegerLiteral)
    print(ind * ' ' + f"reset(q[{qvars[qvar.name.name][qvind.value]}])")


def _assert_switch_statement(stmt: SwitchStatement, ind: int, *qargs):
    
    assert isinstance(target := stmt.target, Identifier)
    assert target.name == "switch_dummy" # if dumped from qiskit, target is always switch_dummy
    print(ind * ' ' + f"match {target.name}:")
    for head, body in stmt.cases:
        assert len(head) == 1
        assert isinstance(head[0], IntegerLiteral)
        assert isinstance(body, CompoundStatement)
        print((ind + 2) * ' ' + f"case {head[0].value}:")
        abstract_debug(body.statements, *qargs)


def _assert_while_loop(stmt: WhileLoop, ind: int, *qargs):
    
    assert isinstance(cond := stmt.while_condition, BinaryExpression)
    assert isinstance(lhs := cond.lhs, Identifier)
    assert isinstance(op := cond.op, BinaryOperator)
    assert op.name in ("==", "!=", "<", "<=", ">", ">=")
    assert isinstance(rhs := cond.rhs, IntegerLiteral)
    print(ind * ' ' + f"while {lhs.name} {op.name} {rhs.value}:")
    abstract_debug(stmt.block, *qargs)


def abstract_debug(program: list[Statement], qsize: int, qvars: dict[str, list[int]]):
    """
    Debug run for `abstract` function.

    :param list[Statement] program: The input program.
    :param int qsize: Total number of quantum variables.
    :param dict[str, list[int]] qvars: A dictionary with quantum registers as keys and the indices
        of its quantum variables as values.
    """
    for stmt in program:

        ind = stmt.span.start_column
        match stmt:

            case ClassicalAssignment():
                _assert_classical_assignment(stmt, ind)

            case ClassicalDeclaration():
                _assert_classical_declaration(stmt, ind)
            
            case QubitDeclaration():
                _assert_qubit_declaration(stmt, ind)

            case QuantumGate():
                _assert_quantum_gate(stmt, qvars, ind)

            case QuantumMeasurementStatement():
                _assert_quantum_measurement(stmt, ind)

            case QuantumReset():
                _assert_quantum_reset(stmt, qvars, ind)
            
            case SwitchStatement():
                _assert_switch_statement(stmt, ind, qsize, qvars)
            
            case WhileLoop():
                _assert_while_loop(stmt, ind, qsize, qvars)

            case Include():
                pass
            
            case _:
                print(ind * ' ' + f"<{type(stmt).__name__}>")
