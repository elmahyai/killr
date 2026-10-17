"""Elimination matrix L, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.e_matrices import e_matrices

_MISSING = object()


def l_matrix(n=_MISSING):
    """Construct the elimination matrix mapping ``vec(A)`` to ``vech(A)``.

    The result has shape ``(n * (n + 1) // 2, n * n)``. The argument must be an
    integer at least 2.
    """
    if n is _MISSING:
        raise ValueError("argument n is missing")
    n = _scalar_integer(n)
    k, identity = _u_vectors(n)
    e_blocks = e_matrices(n)
    p = n * (n + 1) // 2
    nsq = n * n
    result = np.zeros((p, nsq), dtype=float)
    for j in range(1, n + 1):
        for i in range(j, n + 1):
            column = identity[:, k[i - 1, j - 1] - 1]
            row = _vec(e_blocks[i - 1][j - 1])
            result += np.outer(column, row)
    return result


def _vec(array):
    return np.asarray(array, dtype=float).reshape(-1, order="F")


def _u_vectors(n):
    p = n * (n + 1) // 2
    k = np.zeros((n, n), dtype=int)
    for j in range(1, n + 1):
        for i in range(j, n + 1):
            k[i - 1, j - 1] = (j - 1) * n + i - j * (j - 1) // 2
    identity = np.eye(p, dtype=float)
    return k, identity


def _scalar_integer(n):
    if isinstance(n, bool):
        raise ValueError("argument n is not numeric")
    if isinstance(n, np.ndarray):
        if n.ndim == 0:
            n = n.item()
        else:
            raise ValueError("argument n is not the proper data type")
    if isinstance(n, (list, tuple)):
        if len(n) != 1:
            raise ValueError("argument n is not a scalr number")
        n = n[0]
    if not isinstance(n, (int, float, np.integer, np.floating)):
        raise ValueError("argument n is not numeric")
    if isinstance(n, (float, np.floating)):
        number = float(n)
        if not np.isfinite(number):
            raise ValueError("argument n is not an integer")
        if number != int(number):
            raise ValueError("argument n is not an integer")
        number = int(number)
    else:
        number = int(n)
    if number < 2:
        raise ValueError("argument n is less than 2")
    return number
