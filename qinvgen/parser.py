from openqasm3.ast import *
from openqasm3.parser import parse

from lib.stdops import *
from lib.datatypes import qubit
from lib.utils import *
from svts import SVTS

from tests.debug import debug
from tests.test_parser import parse_debug


class QASMProgram:
    _program: list[Statement]
    _qsize: int
    _qvars: dict[str, list[qubit]]
    _cvars: dict[str, list[qubit]]
    _gates: dict[str, Operator]
    _params: tuple[str] # parameters of quantum gate defintions

    def __init__(self, program: str | Program | list[Statement]):

        if isinstance(program, str):
            with open(program, 'r') as file:
                stream = "".join(file.readlines()).strip()
            program = parse(stream)
        if isinstance(program, Program):
            program = program.statements
        
        self._program = program
        self._qsize = 0
        self._qvars = {}
        self._cvars = {}
        self._gates = {}
        self._params = ()

    def count_qvars(self) -> int:
        """
        Count the number of quantum variables in the program.

        :return: Number of quantum variables
        :rtype: int
        """
        qsize = 0
        for stmt in self._program:
            if isinstance(stmt, QubitDeclaration):
                qsize += stmt.size.value
        return qsize

    @property
    def program(self) -> list[Statement]:
        """
        List of statements in the program.
        """
        return self._program.copy()
    
    @property
    def qvars(self) -> dict[str, int]:
        """
        Dictionary of (qi, qs) pairs, where qi is a quantum register identifier
        and qs is its size (number of qubits).
        """
        return {reg: len(qvars) for reg, qvars in self._qvars.items()}
    
    @property
    def cvars(self) -> dict[str, int]:
        """
        Dictionary of (bi, bs) pairs, where bi is a classical variable identifier
        and bs is its size (number of bits).
        """
        return {bit: len(qvars) for bit, qvars in self._cvars.items()}
    
    @property
    def gates(self) -> dict[str, Operator]:
        """
        Dictionary of (gi, go) pairs, where gi is a gate identifier and go is its
        Operator form.
        """
        return self._gates
    

    def _parse_classical_declaration(self, stmt: ClassicalDeclaration) -> SVTS:

        var = stmt.identifier.name
        if isinstance(stmt.type, BitType): # var is a bit
            self._cvars[var] = [-1] * stmt.type.size.value
        else: # var is an int
            self._cvars[var] = []
        
        return SVTS.skip()
    
    def _parse_classical_assignment(self, stmt: ClassicalAssignment) -> SVTS:
        
        lhs = stmt.lvalue.name
        rhs = stmt.rvalue.name
        self._cvars[lhs] = self._cvars[rhs]
        print(self._cvars)

        return SVTS.skip()
    
    def _parse_qubit_declaration(self, stmt: QubitDeclaration) -> SVTS:

        qubits = list(map(qubit, range(self._qsize, self._qsize + stmt.size.value)))
        self._qvars[stmt.qubit.name] = qubits
        self._qsize += stmt.size.value

        return SVTS.skip()
    
    def _parse_quantum_gate_definition(self, stmt: QuantumGateDefinition) -> SVTS:

        self._params = list(map(lambda q: q.name, stmt.qubits))
        body = [self.parse(program=[sub]) for sub in stmt.body]
        c_op = Kraus(np.identity(2 ** len(self._params)))
        
        # compose all ops in the definition to form compound op
        for sub in body:
            op, qargs = sub._cfg.get_edge_data(sub._lin, sub._lout)
            op = expand(op, qsize=len(self._params), qargs=qargs)
            c_op &= op
        
        # add compound op to gate list
        op_name = stmt.name.name.upper()
        self._gates[op_name] = c_op

        return SVTS.skip()

    def _parse_quantum_gate(self, stmt: QuantumGate) -> SVTS:

        # parse arguments of rotation gates
        def parse_expr(expr: Expression) -> int | float:
            match expr:
                case BinaryExpression():
                    val = BINOP[expr.op.name](parse_expr(expr.lhs), parse_expr(expr.rhs))
                case UnaryExpression():
                    val = UNROP[expr.op.name](parse_expr(expr.expression))
                case Identifier():
                    val = CONST[expr.name.upper()]
                case IntegerLiteral() | FloatLiteral():
                    val = expr.value
            return val
        
        # add standard op to gate list
        op_name = stmt.name.name.upper()
        if not self._gates.get(op_name, False):
            if len(stmt.arguments) == 0:
                self._gates[op_name] = FIXEDGATE[op_name]
            else:
                args = list(map(parse_expr, stmt.arguments))
                self._gates[op_name] = PARAMGATE[op_name](*args)
        
        op = self._gates[op_name]

        qargs = []
        for qvar in stmt.qubits:
            qi = qvar.name
            if isinstance(qvar, Identifier): # qvar is a parameter
                qargs.append(self._params.index(qi))
                continue
            for qind in qvar.indices:
                qi = qi.name
                qv = qind[0].value
                qargs.append(self._qvars[qi][qv].val)
        
        return SVTS.unit(op, qargs)
    
    def _parse_quantum_measurement_statement(self, stmt: QuantumMeasurementStatement) -> SVTS:

        cvar = stmt.target.name.name
        cval = stmt.target.indices[0][0].value
        qvar = stmt.measure.qubit.name.name
        qval = stmt.measure.qubit.indices[0][0].value
        self._cvars[cvar][cval] = self._qvars[qvar][qval]

        return SVTS.skip()

    def _parse_quantum_reset(self, stmt: QuantumReset) -> SVTS:

        qi = stmt.qubits.name.name
        qv = stmt.qubits.indices[0][0].value
        qarg = self._qvars[qi][qv].val

        return SVTS.init(qargs=[qarg])

    def _parse_switch_statement(self, stmt: SwitchStatement) -> SVTS:

        cases = []
        cvar = stmt.target.name
        qargs = [qvar.val for qvar in self._cvars[cvar]]
        for head, body in stmt.cases:
            dims = (2,) * len(qargs)
            m_op = outer(Statevector.from_int(head[0].value, dims))
            sub = self.parse(program=body.statements)
            cases.append((m_op, sub))
        
        return SVTS.case(*cases, qargs=qargs)

    def _parse_while_loop(self, stmt: WhileLoop) -> SVTS:

        cond = stmt.while_condition
        cvar = cond.lhs.name
        cval = cond.rhs.value
        qargs = [qvar.val for qvar in self._cvars[cvar]]
        dims = (2,) * len(qargs)
        meas = [outer(Statevector.from_int(i, dims)) for i in range(2 ** len(qargs))]
        meas = [expand(op, qsize=len(qargs)) for op in meas] # reorder basis if needed

        match cond.op.name:
            case "==":
                true = meas[cval]
                false = sum(meas[:cval] + meas[cval + 1:])
            case "!=":
                true = sum(meas[:cval] + meas[cval + 1:])
                false = meas[cval]
            case "<":
                true = sum(meas[:cval])
                false = sum(meas[cval:])
            case "<=":
                true = sum(meas[:cval + 1])
                false = sum(meas[cval + 1:])
            case ">":
                true = sum(meas[cval + 1:])
                false = sum(meas[:cval + 1])
            case ">=":
                true = sum(meas[cval:])
                false = sum(meas[:cval])
        body = self.parse(program=stmt.block)

        return SVTS.loop(true, false, body, qargs)

    @debug(None)
    def parse(self, **kwargs) -> SVTS:
        """
        Parse the program and convert it into an SVTS.
        
        :return: SVTS of the input program.
        :rtype: SVTS
        """
        program = kwargs.get("program", self._program)
        ts = None

        match (stmt := program[0]):

            case ClassicalAssignment():
                ts = self._parse_classical_assignment(stmt)

            case ClassicalDeclaration():
                ts = self._parse_classical_declaration(stmt)
            
            case QubitDeclaration():
                ts = self._parse_qubit_declaration(stmt)

            case QuantumGateDefinition():
                ts = self._parse_quantum_gate_definition(stmt)

            case QuantumGate():
                ts = self._parse_quantum_gate(stmt)

            case QuantumMeasurementStatement():
                ts = self._parse_quantum_measurement_statement(stmt)

            case QuantumReset():
                ts = self._parse_quantum_reset(stmt)
            
            case SwitchStatement():
                ts = self._parse_switch_statement(stmt)
            
            case WhileLoop():
                ts = self._parse_while_loop(stmt)
            
            case _:
                ts = SVTS.skip()

        if len(program) > 1:
            ts = SVTS.comp(ts, self.parse(program=program[1:]))
        
        return ts


if __name__ == "__main__":

    # prog = QASMProgram("examples/qasm/example_1.qasm")
    prog = QASMProgram("examples/qasm/qwalk_2.qasm")
    # prog = QASMProgram("examples/qasm/qwalk_3.qasm")

    with SVTS.meta_init(qsize=prog.count_qvars()):
        ts = prog.parse()
        ts.minimise()
        ts.add_outloop()
    
    if ts:
        print(f"{prog.qvars=}")
        print(f"{prog.cvars=}")
        # print(f"{prog.gates=}")
        print(f"{ts.lin=}")
        print(f"{ts.lout=}")
        print(f"{ts.locations=}")
        for pre, post, (op, qargs) in ts.transitions():
            print(f"{pre} -> {post}: {qargs=}\n{np.real(sum(op.data))}")
