import math
from typing import *

import numpy as np
from qiskit.quantum_info import *

from lib.stdops import FIXEDGATE


def expand(op: Operator | Kraus, qsize: int, qargs: Optional[list[int]] = None) -> Operator | Kraus:
    """
    Expand a (super)operator into a quantum system.

    :param Operator | Kraus op: (Super)operator to be expanded.
    :param int qsize: Number of quantum variables in the system.
    :param list[int] | None qargs: Ordered set of quantum variables on which op acts,
        defaults to the lowest-indexed qubit(s) if None is given.

    :return: Expanded (super)operator.
    :rtype: Operator | Kraus
    """
    qargs = list(range(int(math.log2(op.dim[0])))) if not qargs else qargs

    if len(set(qargs)) < len(qargs):
        raise ValueError(f"qargs contain duplicate qubits")
    if not all(0 <= q < qsize for q in qargs):
        raise ValueError(f"qargs must be a subset of {{0, ..., {qsize - 1}}}")
    if (op_dim := op.dim[0]) != (qv_dim := 2 ** len(qargs)):
        raise ValueError(f"mismatch between dimension of op ({op_dim}) and qargs ({qv_dim})")
    
    # if qargs are already ordered, no basis reordering is required
    if qargs == list(range(min(qargs), max(qargs) + 1)):
        return expand_no_perm(op, qsize, qargs)
    
    # expand op with respect to the bit ordering {free_qvars, qargs}
    free_qvars = [q for q in range(qsize) if q not in qargs]
    for _ in range(len(free_qvars)):
        op = op.expand(FIXEDGATE["I"])
    
    # get permutation from op's basis to the standard basis {0, 1, ..., 2^qsize - 1}
    basis = [permute_bits(q, free_qvars + qargs) for q in range(2 ** qsize)]
    perm = [basis.index(q) for q in range(2 ** qsize)]
    
    # rewrite op in the standard basis
    if isinstance(op, Operator):
        return Operator(op.data[perm, :][:, perm])
    return Kraus([op_mat[perm, :][:, perm] for op_mat in op.data])


def expand_no_perm(op: Operator | Kraus, qsize: int, qvars: list[int]) -> Operator | Kraus:
    """
    Expand a (super)operator without permuting its basis. NOTE: only use this
    function when it can be guaranteed that basis ordering is not required.

    :param Operator | Kraus op: (Super)operator to be expanded.
    :param int qsize: Number of quantum variables in the system.
    :param list[int] | None qargs: Ordered set of quantum variables on which op acts,
        defaults to the lowest-indexed qubit(s) if None is given.

    :return: Expanded (super)operator.
    :rtype: Operator | Kraus
    """
    for _ in range(qvars[0]):
        op = op.expand(FIXEDGATE["I"])
    for _ in range(qsize - qvars[-1] - 1):
        op = op.tensor(FIXEDGATE["I"])
    return op


def outer(l_sv: Statevector, r_sv: Optional[Statevector] = None) -> Operator:
    """
    Compute the outer product of state vectors.

    :param Statevector l_sv: Left state vector.
    :param Statevector | None r_sv: Right state vector. If not given, the outer
    product of `l_sv` with itself is computed.

    :return: outer product of `l_sv` and `r_sv` (or with itself).
    :rtype: Operator
    """
    return Operator(np.outer(l_sv, l_sv if r_sv is None else r_sv))


def permute_bits(num: int, perm: list[int]) -> int:
    """
    Permute the bits in the binary representation of a (decimal) number.

    :param int num: Number whose bits are permuted.
    :param list[int] perm: Permutation map, where i and perm[i] denote
        bit indices before and after permuting.
    :param 

    :return: Resulting (decimal) number after bit permutation.
    :rtype: int
    """
    p_num = 0
    flip = lambda i: len(perm) - i - 1 # intepret num as written in big endian
    for i, fi in enumerate(perm):
        # extract bit value at index fi and place it at index i
        p_num += ((num & (1 << flip(fi))) >> flip(fi)) << flip(i)
    return p_num
