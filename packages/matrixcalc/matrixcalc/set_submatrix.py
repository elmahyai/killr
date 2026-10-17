"""Insert one matrix into another at a row and column, from matrixcalc 1.0-6."""

from __future__ import annotations

import math

import numpy as np


def set_submatrix(x, y, row, col):
    """Return a copy of ``x`` with ``y`` written at 1-based ``row`` and ``col``.

    Both arguments must be numeric matrices. ``row`` and ``col`` must be positive
    integers, and the block must fit inside ``x``.
    """
    x_mat = _as_matrix(x, "x")
    y_mat = _as_matrix(y, "y")
    if not _is_numeric_matrix(x_mat):
        raise ValueError("argument x is not a numeric matrix")
    if not _is_numeric_matrix(y_mat):
        raise ValueError("argument y is not a numeric matrix")
    row_i = _positive_index(row, "row")
    col_i = _positive_index(col, "col")
    nrow_y, ncol_y = y_mat.shape
    row_end = row_i + nrow_y - 1
    col_end = col_i + ncol_y - 1
    if row_end > x_mat.shape[0] or row_i < 1:
        raise ValueError("row range not inside row of argument x")
    if col_end > x_mat.shape[1] or col_i < 1:
        raise ValueError("col range not inside the column of argument x")
    z = x_mat.copy()
    r0, c0 = row_i - 1, col_i - 1
    z[r0 : r0 + nrow_y, c0 : c0 + ncol_y] = y_mat
    return z


def _positive_index(value, name):
    if isinstance(value, bool):
        raise ValueError(f"argument {name} is not an integer")
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            value = value.item()
        else:
            raise ValueError(f"argument {name} is not an integer")
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError(f"argument {name} is not an integer")
        value = value[0]
    if isinstance(value, (int, np.integer)):
        number = int(value)
    elif isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise ValueError(f"argument {name} is not an integer")
        if number != math.trunc(number):
            raise ValueError(f"argument {name} is not an integer")
        number = int(number)
    else:
        raise ValueError(f"argument {name} is not an integer")
    if number <= 0:
        raise ValueError(f"argument {name} is not positive")
    return number


def _as_matrix(x, name):
    if isinstance(x, np.ndarray):
        if x.ndim != 2:
            raise ValueError(f"argument {name} is not a matrix")
        return x
    if _rectangular_rows(x):
        return np.array(x)
    raise ValueError(f"argument {name} is not a matrix")


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
