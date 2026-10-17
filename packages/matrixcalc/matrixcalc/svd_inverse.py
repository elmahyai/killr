"""SVD-based matrix inverse, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def svd_inverse(x):
    """Return the Moore-Penrose inverse of a numeric matrix or vector via SVD."""
    if not _is_numeric(x):
        raise ValueError("argument x is not numeric")
    xmat = _as_numeric_matrix(x)
    u, singular_values, vh = np.linalg.svd(xmat, full_matrices=False)
    if np.any(singular_values == 0):
        raise ValueError("x has at least one zero singular value")
    if singular_values.size == 1:
        dinv = np.array([[1.0 / singular_values[0]]], dtype=float)
    else:
        dinv = np.diag(1.0 / singular_values)
    v = vh.T
    return v @ dinv @ u.T


def _is_numeric(value):
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, np.ndarray):
        if value.dtype == bool or value.dtype.kind == "b":
            return False
        if value.dtype.kind in "iuf":
            return True
        if value.dtype.kind == "O":
            return _object_is_numeric(value)
        return False
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return True
        if _rectangular_rows(value):
            return _nested_is_numeric(value)
        return _sequence_is_numeric(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    return False


def _as_numeric_matrix(value):
    if isinstance(value, np.ndarray):
        if value.ndim == 2:
            return np.asarray(value, dtype=float)
        if value.ndim == 1:
            return np.asarray(value, dtype=float).reshape(-1, 1)
        raise ValueError("argument x is neither a vector nor a matrix")
    if isinstance(value, (list, tuple)):
        if _rectangular_rows(value):
            return np.asarray(value, dtype=float)
        return np.asarray(value, dtype=float).reshape(-1, 1)
    raise ValueError("argument x is neither a vector nor a matrix")


def _rectangular_rows(x):
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


def _sequence_is_numeric(seq):
    for item in seq:
        if isinstance(item, (bool, np.bool_)):
            return False
        if isinstance(item, (str, bytes)):
            return False
        if isinstance(item, (complex, np.complexfloating)):
            return False
        if not isinstance(item, (int, float, np.integer, np.floating)):
            return False
    return True


def _nested_is_numeric(rows):
    for row in rows:
        for item in row:
            if isinstance(item, (bool, np.bool_)):
                return False
            if isinstance(item, (str, bytes)):
                return False
            if isinstance(item, (complex, np.complexfloating)):
                return False
            if not isinstance(item, (int, float, np.integer, np.floating)):
                return False
    return True


def _object_is_numeric(array):
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
