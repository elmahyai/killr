"""Order n Frobenius matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import math

import numpy as np


def frobenius_matrix(n):
    """Return the order ``n`` Frobenius matrix used in numerical mathematics.

    The matrix is the identity shifted down one row, with the last column
    filled from signed binomial coefficients. The argument must be an integer
    at least 2.
    """
    n = _scalar_integer(n)
    matrix = _shift_down(np.eye(n, dtype=float))
    nm1 = n - 1
    indices = np.arange(n, dtype=float)
    matrix[:, n - 1] = np.power(-1.0, nm1 - indices) * np.fromiter(
        (math.comb(n, j) for j in range(n)),
        dtype=float,
        count=n,
    )
    return matrix


def _shift_down(matrix, rows=1, fill=0.0):
    if rows == 0:
        return matrix.copy()
    result = np.full_like(matrix, fill)
    nrow = matrix.shape[0]
    if rows < nrow:
        result[rows:, :] = matrix[: nrow - rows, :]
    return result


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
