from openqasm3.ast import *


def _assert_classical_assignment(stmt: ClassicalAssignment, ind: int):

    # only form of classical assignment expected is switch_dummy = c
    assert isinstance(lhs := stmt.lvalue, Identifier)
    assert (op := stmt.op.name) == "="
    assert isinstance(rhs := stmt.rvalue, Identifier)
    print(ind * ' ' + f"{lhs.name} {op} {rhs.name}")

def _assert_classical_declaration(stmt: ClassicalDeclaration, ind: int):
    
    assert isinstance(datatype := stmt.type, ClassicalType)
    assert isinstance(datatype, (BitType, IntType))
    if isinstance(datatype, BitType):
        assert isinstance(size := datatype.size, IntegerLiteral)
        print(f"{stmt.identifier.name}: bit[{size.value}]")
    else:
        print(ind * ' ' + f"{stmt.identifier.name}: int")

def _assert_qubit_declaration(stmt: QubitDeclaration, ind: int):
    
    assert isinstance(size := stmt.size, IntegerLiteral)
    print(ind * ' ' + f"{stmt.qubit.name}: qubit[{size.value}]")

def _assert_quantum_gate_definition(stmt: QuantumGateDefinition, ind: int):

    assert not stmt.arguments # should not have any arguments
    assert all(isinstance(sub, QuantumGate) for sub in stmt.body)
    qargs = ','.join(qubit.name[-1] for qubit in stmt.qubits)
    print(ind * ' ' + f"gate {stmt.name.name.upper()}({qargs}):")
    parse_debug(stmt.body)

def _assert_quantum_gate(stmt: QuantumGate, ind: int):

    def process_expr(expr: Expression) -> str:
        match expr:
            case BinaryExpression():
                assert expr.op.name == '/'
                lhs = process_expr(expr.lhs)
                rhs = process_expr(expr.rhs)
                val = lhs + expr.op.name + rhs
            case UnaryExpression():
                assert expr.op.name == '-'
                val = expr.op.name + process_expr(expr.expression)
            case Identifier():
                assert expr.name == 'pi'
                val = expr.name
            case IntegerLiteral():
                val = str(expr.value)
            case _:
                raise AssertionError(f"Unexpected type {type(expr)}")
        return val
    
    op = stmt.name.name.upper()
    args = list(map(process_expr, stmt.arguments))
    qvars = []
    for qvar in stmt.qubits:
        if isinstance(qvar, IndexedIdentifier):
            assert all(len(qind) == 1 and isinstance(qind[0], IntegerLiteral) for qind in qvar.indices)
            qvars.extend([f"{qvar.name.name}[{qind[0].value}]" for qind in qvar.indices])
        else:
            qvars.append(qvar.name[-1])
    if args:
        print(ind * ' ' + f"{op}[{', '.join(args)}]({', '.join(qvars)})")
    else:
        print(ind * ' ' + f"{op}({', '.join(qvars)})")

def _assert_quantum_measurement(stmt: QuantumMeasurementStatement, ind: int):
    
    assert isinstance(qvar := stmt.measure.qubit, IndexedIdentifier)
    assert len(qinds := qvar.indices) == 1 and len(qind := qinds[0]) == 1 # only measure one qubit at a time
    assert isinstance(qind := qind[0], IntegerLiteral)
    assert isinstance(cvar := stmt.target, IndexedIdentifier)
    assert len(cinds := cvar.indices) == 1 and len(cind := cinds[0]) == 1 # only measure to one clbit at a time
    assert isinstance(cind := cind[0], IntegerLiteral)
    print(ind * ' ' + f"{cvar.name.name}[{cind.value}] = measure({qvar.name.name}[{qind.value}])")

def _assert_quantum_reset(stmt: QuantumReset, ind: int):
    
    assert isinstance(qvar := stmt.qubits, IndexedIdentifier)
    assert len(qinds := qvar.indices) == 1 and len(qind := qinds[0]) == 1 # only reset one qubit at a time
    assert isinstance(qind := qind[0], IntegerLiteral)
    print(ind * ' ' + f"reset({qvar.name.name}[{qind.value}])")

def _assert_switch_statement(stmt: SwitchStatement, ind: int):
    
    assert isinstance(target := stmt.target, Identifier)
    assert target.name == "switch_dummy" # if dumped from qiskit, target is always switch_dummy
    print(ind * ' ' + f"match {target.name}:")
    for head, body in stmt.cases:
        assert len(head) == 1
        assert isinstance(head[0], IntegerLiteral)
        assert isinstance(body, CompoundStatement)
        print((ind + 4) * ' ' + f"case {head[0].value}:")
        parse_debug(body.statements)

def _assert_while_loop(stmt: WhileLoop, ind: int):
    
    assert isinstance(cond := stmt.while_condition, BinaryExpression)
    assert isinstance(lhs := cond.lhs, Identifier)
    assert isinstance(op := cond.op, BinaryOperator)
    assert op.name in ("==", "!=", "<", "<=", ">", ">=")
    assert isinstance(rhs := cond.rhs, IntegerLiteral)
    print(ind * ' ' + f"while {lhs.name} {op.name} {rhs.value}:")
    parse_debug(stmt.block)


def parse_debug(program: list[Statement], **kwargs):
    """
    Debug run for `QASMProgram.parse` method.

    :param list[Statement] program: The input program.
    :param int qsize: Total number of quantum variables.
    :param dict[str, list[int]] qvars: A dictionary with quantum registers as keys and the indices
        of its quantum variables as values.
    """
    program = kwargs.get("program", program)
    if not isinstance(program, list):
        program = program.program

    for stmt in program:

        ind = stmt.span.start_column * 2
        match stmt:

            case ClassicalAssignment():
                _assert_classical_assignment(stmt, ind)

            case ClassicalDeclaration():
                _assert_classical_declaration(stmt, ind)
            
            case QubitDeclaration():
                _assert_qubit_declaration(stmt, ind)

            case QuantumGate():
                _assert_quantum_gate(stmt, ind)

            case QuantumGateDefinition():
                _assert_quantum_gate_definition(stmt, ind)

            case QuantumMeasurementStatement():
                _assert_quantum_measurement(stmt, ind)

            case QuantumReset():
                _assert_quantum_reset(stmt, ind)
            
            case SwitchStatement():
                _assert_switch_statement(stmt, ind)
            
            case WhileLoop():
                _assert_while_loop(stmt, ind)

            case Include():
                pass
            
            case _:
                print(ind * ' ' + f"<{type(stmt).__name__}>")
