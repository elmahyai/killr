"""Vectorize a matrix (lower triangle), from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.is_square_matrix import is_square_matrix


def vech(x):
    """Return the lower triangle of a square matrix stacked in one column.

    The result has ``n * (n + 1) // 2`` rows and one column. A non-square
    matrix raises ``argument x is not a square numeric matrix``.
    """
    if not is_square_matrix(x):
        raise ValueError("argument x is not a square numeric matrix")
    array = _as_matrix(x)
    n = array.shape[0]
    parts = []
    for j in range(n):
        for i in range(j, n):
            parts.append(array[i, j])
    return np.asarray(parts, dtype=array.dtype).reshape(-1, 1)


def _as_matrix(x):
    if isinstance(x, np.ndarray):
        if x.ndim != 2:
            raise ValueError("argument x is not a matrix")
        return x
    if _rectangular_rows(x):
        return np.array(x)
    raise ValueError("argument x is not a matrix")


def _rectangular_rows(x):
    if isinstance(x, (str, bytes)) or not isinstance(x, (list, tuple)):
        return False
    if len(x) == 0:
        return False
    width = None
    for row in x:
        if isinstance(row, (str, bytes)) or not isinstance(row, (list, tuple)):
            return False
        if width is None:
            width = len(row)
        elif len(row) != width:
            return False
    return True
