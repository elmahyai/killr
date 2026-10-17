"""Test for square matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def is_square_matrix(x):
    """Return whether ``x`` is a square matrix.

    A value that is not a matrix raises ``argument x is not a matrix``.
    """
    array = _as_matrix(x)
    return array.shape[0] == array.shape[1]


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
