from typing import *

import numpy as np
from qiskit.quantum_info import *

from lib.ops import *


def permute_bits(num: int, perm: list[int]) -> int:
    """
    Permute the bits in the binary representation of a (decimal) number.

    params:
    - `num` (int): Number whose bits are permuted.
    - `perm` (list[int]): Permutation map, where i and perm[i] denote
    bit indices before and after permuting.

    returns:
    - Resulting (decimal) number after bit permutation.
    """
    p_num = 0
    for i, fi in enumerate(perm):
        # extract bit value at index fi and place it at index i
        p_num += ((num & (1 << fi)) >> fi) << i
    return p_num


def get_statevec(ndim: int, val: int) -> Statevector:
    """
    Construct a state vector corresponding to the given bit value.

    params:
    - `ndim` (int): Dimension of the state space.
    - `val` (int): Value of the state vector.

    returns:
    - Constructed state vector
    """
    return Statevector([1 if x == val else 0 for x in range(ndim)])


def get_basis(ndim: int) -> list[Statevector]:
    """
    Compute the basis of the state space of a quantum system.

    params:
    - `ndim` (int): Dimension of the state space.

    returns:
    - List of state vectors constituting the basis.
    """
    return [get_statevec(ndim, x) for x in range(ndim)]


def expand(qsize: int, op: Operator | Kraus, qvars: list[int]) -> Kraus | Operator:
    """
    Expand a (super)operator into a quantum system.

    params:
    - `qsize` (int): Number of quantum variables in the system.
    - `op` (Operator | Kraus): (Super)operator to be expanded.
    - `qvars` (list[int]): Ordered set of quantum variables on which op acts.

    returns:
    - Expanded (super)operator
    """
    if len(set(qvars)) < len(qvars):
        raise ValueError(f"qvars contain duplicate qubits")
    if not all(0 <= q < qsize for q in qvars):
        raise ValueError(f"qvars must be a subset of {{0, 1, ..., {qsize - 1}}}")
    if (op_dim := op.dim[0]) != (qv_dim := 2 ** len(qvars)):
        raise ValueError(f"mismatch between dimension of op ({op_dim}) and qvars ({qv_dim})")
    
    # if qvars are already ordered, no basis reordering is required
    if qvars == list(range(min(qvars), max(qvars) + 1)):
        return _expand_no_perm(qsize, op, qvars)
    
    # expand op with respect to the bit ordering {free_qvars, qvars}
    free_qvars = [q for q in range(qsize) if q not in qvars]
    for _ in range(len(free_qvars)):
        op = op.expand(I)
    
    # get permutation from op's basis to the standard basis {0, 1, ..., 2^qsize - 1}
    basis = [permute_bits(q, free_qvars + qvars) for q in range(2 ** qsize)]
    perm = [basis.index(q) for q in range(2 ** qsize)]
    
    # rewrite op in the standard basis
    if isinstance(op, Operator):
        return Operator(op.data[perm, :][:, perm])
    return Kraus([op_mat[perm, :][:, perm] for op_mat in op.data])


def _expand_no_perm(qsize: int, op: Operator | Kraus, qvars: list[int]) -> Kraus | Operator:
    """
    Expand a (super) operator without checking whether basis reordering is
    required. NOTE: only use when qvars is known to be {m, m + 1, ..., n}
    for some m, n.
    """
    for _ in range(qvars[0]):
        op = op.expand(I)
    for _ in range(qsize - qvars[-1] - 1):
        op = op.tensor(I)
    
    return op


def outer(l_sv: Statevector, r_sv: Optional[Statevector] = None) -> np.ndarray:
    """
    Compute the outer product of state vectors.

    params:
    - `l_sv` (Statevector): Left state vector.
    - `r_sv` (Statevector | None): Right state vector. If not given, the outer
    product of `l_sv` with itself is computed.

    returns:
    - outer product of `l_sv` and `r_sv` (or with itself).
    """
    return np.outer(l_sv, l_sv if r_sv is None else r_sv)
