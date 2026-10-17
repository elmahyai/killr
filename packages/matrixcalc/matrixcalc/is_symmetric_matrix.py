"""Test for symmetric numeric matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import math

import numpy as np

from matrixcalc.is_square_matrix import is_square_matrix


def is_symmetric_matrix(x):
    """Return whether a square numeric matrix equals its transpose.

    A non-matrix raises ``argument x is not a matrix``.
    A non-numeric matrix raises ``argument x is not a numeric matrix``.
    A non-square matrix raises ``argument x is not a square numeric matrix``.
    """
    array = _as_matrix(x)
    if not _is_numeric_matrix(array):
        raise ValueError("argument x is not a numeric matrix")
    if not is_square_matrix(x):
        raise ValueError("argument x is not a square numeric matrix")
    return _symmetric_by_transpose_equality(array)


def _symmetric_by_transpose_equality(array):
    n = array.shape[0]
    if n == 0:
        return True
    saw_missing = False
    for i in range(n):
        for j in range(n):
            equal = _r_equal(array[i, j], array[j, i])
            if equal is False:
                return False
            if equal is None:
                saw_missing = True
    if saw_missing:
        return float("nan")
    return True


def _r_equal(left, right):
    if _is_missing(left) or _is_missing(right):
        return None
    if isinstance(left, (bool, np.bool_)) or isinstance(right, (bool, np.bool_)):
        return bool(left) == bool(right)
    if isinstance(left, (complex, np.complexfloating)) or isinstance(
        right, (complex, np.complexfloating)
    ):
        return complex(left) == complex(right)
    return float(left) == float(right)


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, np.floating) and np.isnan(value):
        return True
    return False


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
