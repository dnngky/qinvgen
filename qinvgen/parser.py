import dataclasses

from openqasm3.ast import *
from openqasm3.parser import parse


def remove_spans(node):
    """
    Return a new ``QASMNode`` with all spans recursively set to ``None`` to
    reduce noise in test failure messages.
    """
    if isinstance(node, list):
        return [remove_spans(item) for item in node]
    if not isinstance(node, QASMNode):
        return node

    kwargs = {}
    no_init = {}
    for field in dataclasses.fields(node):
        if field.name == "span":
            continue
        target = kwargs if field.init else no_init
        target[field.name] = remove_spans(getattr(node, field.name))
    
    out = type(node)(**kwargs)
    for attribute, value in no_init.items():
        setattr(out, attribute, value)
    
    return out


if __name__ == "__main__":

    with open("qc.qasm", 'r') as file:
        stream = "".join(file.readlines()).strip()
    program = remove_spans(parse(stream))

    for stmt in program.statements:
        print(stmt)
        match stmt:
            case ClassicalDeclaration():
                print("CI")
            case QubitDeclaration():
                print("IN | UT")
            case BranchingStatement():
                print("IF")
            case WhileLoop():
                print("LP")
            case QuantumMeasurementStatement():
                print("QM")