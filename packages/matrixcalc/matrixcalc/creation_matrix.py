"""Order-n creation matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def creation_matrix(n):
    """Return the order ``n`` creation matrix.

    The matrix has the sequence 1, 2, ..., n - 1 on the sub-diagonal below
    the principal diagonal. The argument must be an integer greater than 1.
    """
    n = _scalar_integer(n)
    matrix = np.zeros((n, n), dtype=float)
    rows = np.arange(1, n)
    matrix[rows, rows - 1] = rows.astype(float)
    return matrix


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
