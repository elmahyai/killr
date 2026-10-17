"""Matrix raised to an integer power, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.is_square_matrix import is_square_matrix
from matrixcalc.matrix_inverse import matrix_inverse


def matrix_power(x, k):
    """Return the ``k``-th power of a square numeric matrix."""
    if not is_square_matrix(x):
        raise ValueError("argument x is not a square matrix")
    array = _as_matrix(x)
    if not _is_numeric_matrix(array):
        raise ValueError("argument x is not numeric")
    exponent = _scalar_integer(k)
    n = array.shape[0]
    if exponent == 0:
        return np.eye(n, dtype=float)
    mat = np.asarray(array, dtype=float)
    if exponent < 0:
        return matrix_power(matrix_inverse(mat), -exponent)
    powered = mat
    index = 2
    while index <= exponent:
        powered = powered @ mat
        index += 1
    return powered


def _scalar_integer(k):
    if isinstance(k, bool):
        raise ValueError("argument k is not numeric")
    if isinstance(k, np.ndarray):
        if k.ndim == 0:
            k = k.item()
        else:
            raise ValueError("argument k is not the proper data type")
    if isinstance(k, (list, tuple)):
        if len(k) != 1:
            raise ValueError("argument k is not a scalr number")
        k = k[0]
    if not isinstance(k, (int, float, np.integer, np.floating)):
        raise ValueError("argument k is not numeric")
    if isinstance(k, (float, np.floating)):
        number = float(k)
        if not np.isfinite(number):
            raise ValueError("argument k is not an integer")
        if number != int(number):
            raise ValueError("argument k is not an integer")
        number = int(number)
    else:
        number = int(k)
    return number


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
