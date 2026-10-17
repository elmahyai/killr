"""Pascal matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import math

import numpy as np

from matrixcalc.lu_decomposition import lu_decomposition


def pascal_matrix(n):
    """Return the order ``n`` Pascal matrix (lower triangular binomial rows).

    The matrix is the ``L`` factor from a Doolittle LU decomposition of the
    symmetric Pascal matrix of the same order. The argument must be a positive
    integer.
    """
    order = _positive_integer(n)
    symmetric = _symmetric_pascal_matrix(order)
    return lu_decomposition(symmetric)["L"]


def _symmetric_pascal_matrix(n):
    """Mirror ``symmetric.pascal.matrix`` until that export is translated."""
    nm1 = n - 1
    values = [1.0] * nm1
    for i in range(1, nm1 + 1):
        for j in range(1, nm1 + 1):
            values.append(_n_over_r(i + j, j))
    body = np.asarray(values, dtype=float).reshape(n, nm1, order="C")
    return np.column_stack([np.ones(n, dtype=float), body])


def _n_over_r(n, r):
    return math.prod(range(1, n + 1)) / (
        math.prod(range(1, n - r + 1)) * math.prod(range(1, r + 1))
    )


def _positive_integer(n):
    if isinstance(n, bool):
        raise ValueError("argument n is not an integer")
    if isinstance(n, np.ndarray):
        if n.ndim == 0:
            n = n.item()
        else:
            raise ValueError("argument n is not an integer")
    if isinstance(n, (list, tuple)):
        if len(n) != 1:
            raise ValueError("argument n is not an integer")
        n = n[0]
    if isinstance(n, (int, np.integer)):
        number = int(n)
    elif isinstance(n, (float, np.floating)):
        number = float(n)
        if not np.isfinite(number):
            raise ValueError("argument n is not an integer")
        if number != math.trunc(number):
            raise ValueError("argument n is not an integer")
        number = int(number)
    else:
        raise ValueError("argument n is not an integer")
    if number <= 0:
        raise ValueError("argument n is not positive")
    return number
