"""Test for diagonal square matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.is_square_matrix import is_square_matrix


def is_diagonal_matrix(x, tol=1e-8):
    """Return whether off-diagonal entries of a square numeric matrix are near zero.

    A non-square matrix raises ``argument x is not a square matrix``.
    A non-numeric matrix raises ``argument x is not a numeric matrix``.
    """
    if not is_square_matrix(x):
        raise ValueError("argument x is not a square matrix")
    array = _as_matrix(x)
    if not _is_numeric_matrix(array):
        raise ValueError("argument x is not a numeric matrix")
    tol = _scalar_tol(tol)
    work = np.array(array, copy=True, dtype=float if array.dtype.kind in "iuf" else object)
    if work.dtype.kind != "O":
        np.fill_diagonal(work, 0)
        return _all_abs_lt(work, tol)
    return _all_abs_lt_object(work, tol)


def _scalar_tol(tol):
    if isinstance(tol, np.ndarray):
        if tol.ndim == 0:
            tol = tol.item()
        else:
            tol = float(np.asarray(tol, dtype=float).reshape(-1)[0])
    elif isinstance(tol, (list, tuple)):
        if len(tol) != 1:
            tol = float(np.asarray(tol, dtype=float).reshape(-1)[0])
        else:
            tol = tol[0]
    if isinstance(tol, (bool, np.bool_)):
        tol = int(tol)
    if not isinstance(tol, (int, float, np.integer, np.floating)):
        raise TypeError("tol must be numeric")
    return float(tol)


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


def _all_abs_lt(array, tol):
    if array.size == 0:
        return True
    abs_values = np.abs(array, dtype=float)
    with np.errstate(invalid="ignore"):
        less = abs_values < tol
    missing = np.isnan(abs_values)
    if np.any(~missing & ~less):
        return False
    if np.any(missing):
        return float("nan")
    return True


def _all_abs_lt_object(array, tol):
    saw_missing = False
    for i in range(array.shape[0]):
        for j in range(array.shape[1]):
            if i == j:
                continue
            value = array[i, j]
            if value is None or (isinstance(value, float) and np.isnan(value)):
                saw_missing = True
                continue
            if abs(float(value)) >= tol:
                return False
    if saw_missing:
        return float("nan")
    return True
