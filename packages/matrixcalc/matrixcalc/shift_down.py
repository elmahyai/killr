"""Shift matrix rows downward with fill, from matrixcalc 1.0-6."""

from __future__ import annotations

import math

import numpy as np


def shift_down(a, rows=1, fill=0):
    """Return ``a`` with rows shifted down by ``rows``, filling the top with ``fill``.

    ``a`` must be a numeric matrix. ``rows`` must be a non-negative integer.
    """
    matrix = _as_matrix(a)
    if not _is_numeric_matrix(matrix):
        raise ValueError("argument A is not a numeric matrix")
    shift_rows = _shift_rows(rows)
    fill_value = _numeric_fill(fill)
    if shift_rows == 0:
        return matrix
    result = np.full(matrix.shape, fill_value, dtype=float)
    nrow = matrix.shape[0]
    if shift_rows < nrow:
        result[shift_rows:, :] = matrix[: nrow - shift_rows, :]
    return result


def _shift_rows(value):
    if isinstance(value, bool):
        raise ValueError("Arguments rows is not an integer")
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            value = value.item()
        else:
            raise ValueError("Arguments rows is not an integer")
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError("Arguments rows is not an integer")
        value = value[0]
    if isinstance(value, (int, np.integer)):
        number = int(value)
    elif isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise ValueError("Arguments rows is not an integer")
        if number != math.trunc(number):
            raise ValueError("Arguments rows is not an integer")
        number = int(number)
    else:
        raise ValueError("Arguments rows is not an integer")
    if number < 0:
        raise ValueError("Argument rows is not positive")
    return number


def _numeric_fill(value):
    if isinstance(value, bool):
        raise ValueError("Argument fill is not numeric")
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            value = value.item()
        else:
            raise ValueError("Argument fill is not numeric")
    if isinstance(value, (list, tuple)):
        raise ValueError("Argument fill is not numeric")
    if isinstance(value, (complex, np.complexfloating)):
        raise ValueError("Argument fill is not numeric")
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    raise ValueError("Argument fill is not numeric")


def _as_matrix(x):
    if isinstance(x, np.ndarray):
        if x.ndim != 2:
            raise ValueError("argument A is not a matrix")
        return x
    if _rectangular_rows(x):
        return np.array(x)
    raise ValueError("argument A is not a matrix")


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
