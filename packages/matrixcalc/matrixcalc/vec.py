"""Column-stack vectorization of a matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def vec(x):
    """Return a column matrix stacking the columns of ``x``.

    Each column of ``x`` becomes a contiguous block in the result, in
    column-major order like R ``as.vector``.
    """
    array = _as_matrix(x)
    if not _is_numeric_matrix(array):
        raise ValueError("argument x is not a numeric matrix")
    flat = array.reshape(-1, order="F")
    if array.dtype.kind in "iu":
        return flat.reshape(-1, 1)
    if array.dtype.kind == "O":
        return np.array(flat, dtype=object).reshape(-1, 1)
    return np.asarray(flat, dtype=float).reshape(-1, 1)


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


def _is_numeric_matrix(array):
    kind = array.dtype.kind
    if kind in "iuf":
        return True
    if kind == "O":
        return _object_matrix_is_numeric(array)
    return False


def _object_matrix_is_numeric(array):
    for value in array.ravel():
        if isinstance(value, (bool, np.bool_)):
            return False
        if isinstance(value, (str, np.str_, bytes, np.bytes_)):
            return False
        if isinstance(value, (complex, np.complexfloating)):
            return False
        if not isinstance(value, (int, float, np.integer, np.floating)):
            return False
    return True
