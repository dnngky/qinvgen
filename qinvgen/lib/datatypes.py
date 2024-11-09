from typing import Self
from dataclasses import dataclass


@dataclass(frozen=True)
class qubit:
    val: int

    def __init__(self, val: int | Self):
        if isinstance(val, qubit):
            val = val.val
        object.__setattr__(self, "val", val)

    def __repr__(self) -> str:
        return f"q[{self.val}]"