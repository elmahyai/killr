"""LU decomposition of a square matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.is_square_matrix import is_square_matrix


def lu_decomposition(x):
    """Return Doolittle LU factors ``L`` and ``U`` for a square numeric matrix."""
    if not is_square_matrix(x):
        raise ValueError("argument x is not a square matrix")
    array = _as_matrix(x)
    if not _is_numeric_matrix(array):
        raise ValueError("argument x is not numeric")
    mat = np.asarray(array, dtype=float)
    n = mat.shape[0]
    lower = np.zeros((n, n), dtype=float)
    upper = np.zeros((n, n), dtype=float)
    np.fill_diagonal(lower, 1.0)
    for i in range(n):
        ip1 = i + 1
        im1 = i
        for j in range(n):
            upper[i, j] = mat[i, j]
            if im1 > 0:
                for k in range(im1):
                    upper[i, j] -= lower[i, k] * upper[k, j]
        if ip1 < n:
            for j in range(ip1, n):
                lower[j, i] = mat[j, i]
                if im1 > 0:
                    for k in range(im1):
                        lower[j, i] -= lower[j, k] * upper[k, i]
                if upper[i, i] == 0:
                    raise ValueError("argument x is a singular matrix")
                lower[j, i] /= upper[i, i]
    return {"L": lower, "U": upper}


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
