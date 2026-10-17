"""Test for positive semi-definite symmetric matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import math

import numpy as np

from matrixcalc.is_square_matrix import is_square_matrix
from matrixcalc.is_symmetric_matrix import is_symmetric_matrix


def is_positive_semi_definite(x, tol=1e-8):
    """Return whether a square symmetric numeric matrix is positive semi-definite.

    Eigenvalues with absolute value below ``tol`` are treated as zero.
    A non-square matrix raises ``argument x is not a square matrix``.
    A non-symmetric matrix raises ``argument x is not a symmetric matrix``.
    A non-numeric matrix raises ``argument x is not a numeric matrix``.
    """
    if not is_square_matrix(x):
        raise ValueError("argument x is not a square matrix")
    symmetric = is_symmetric_matrix(x)
    if symmetric is not True:
        if isinstance(symmetric, (float, np.floating)) and math.isnan(symmetric):
            raise ValueError("missing value where TRUE/FALSE needed")
        raise ValueError("argument x is not a symmetric matrix")
    array = _as_matrix(x)
    if not _is_numeric_matrix(array):
        raise ValueError("argument x is not a numeric matrix")
    tol = _scalar_tol(tol)
    eigenvalues = np.linalg.eigvalsh(np.asarray(array, dtype=float))
    for index in range(eigenvalues.size):
        if abs(eigenvalues[index]) < tol:
            eigenvalues[index] = 0.0
    if np.any(eigenvalues < 0):
        return False
    return True


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
