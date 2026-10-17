"""Lower triangular portion of a matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.is_square_matrix import is_square_matrix


def lower_triangle(x):
    """Return ``x`` with entries above the main diagonal set to zero.

    A non-square matrix raises ``argument x is not a square numeric matrix``.
    """
    if not is_square_matrix(x):
        raise ValueError("argument x is not a square numeric matrix")
    array = _as_matrix(x)
    y = array.copy()
    rows, cols = np.indices(y.shape)
    y[rows < cols] = 0
    return y


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
