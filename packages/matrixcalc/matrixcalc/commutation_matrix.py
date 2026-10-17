"""Commutation matrix for r by c numeric matrices, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def commutation_matrix(r, c=None):
    """Return the commutation matrix of order r * c.

    For an r by c matrix ``A``, this matrix ``K`` satisfies
    ``K @ vec(A) == vec(A.T)`` with column-major vectorization like R.

    Each dimension must be an integer at least 2.
    """
    if c is None:
        c = r
    r = _integer_dimension(r, "r")
    c = _integer_dimension(c, "c")
    size = r * c
    i_index, j_index = np.meshgrid(np.arange(r), np.arange(c), indexing="ij")
    row = (i_index * c + j_index).ravel()
    col = (j_index * r + i_index).ravel()
    matrix = np.zeros((size, size), dtype=float)
    matrix[row, col] = 1.0
    return matrix


def _integer_dimension(value, name):
    if isinstance(value, bool):
        raise ValueError(f"argument {name} is not an integer")
    if isinstance(value, (int, np.integer)):
        number = int(value)
    elif isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number) or number != int(number):
            raise ValueError(f"argument {name} is not an integer")
        number = int(number)
    else:
        raise ValueError(f"argument {name} is not an integer")
    if number < 2:
        raise ValueError(f"argument {name} is less than 2")
    return number
