"""Trace of a square matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

_INT_MIN = -2147483647
_INT_MAX = 2147483647


def matrix_trace(x):
    """Sum of the main diagonal of a square matrix.

    A value that is not a matrix raises ``argument x is not a matrix``.
    A matrix that is not square raises ``argument x is not a square matrix``.
    The sum starts at 0, so a diagonal of ``-0`` is ``+0``. An integer or
    logical diagonal stays an integer while the sum fits in a 32-bit
    integer, and becomes a double when it does not.
    """
    array = _as_matrix(x)
    if array.shape[0] != array.shape[1]:
        raise ValueError("argument x is not a square matrix")
    return _sum_diagonal(array)


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


def _sum_diagonal(array):
    diagonal = np.diagonal(array)
    kind = array.dtype.kind
    if kind in "SU":
        raise ValueError("invalid 'type' (character) of argument")
    if kind == "V":
        raise ValueError("invalid 'type' (raw) of argument")
    if kind == "O":
        return _sum_object(diagonal)
    if kind == "b":
        return _finish_integer(sum(int(value) for value in diagonal))
    if kind in "iu":
        return _finish_integer(sum(int(value) for value in diagonal))
    if kind == "c":
        total = 0j
        for value in diagonal:
            total += complex(value)
        return total
    if kind == "f":
        total = np.longdouble(0)
        with np.errstate(invalid="ignore", over="ignore"):
            for value in diagonal:
                total += value
        return float(total)
    raise ValueError("invalid 'type' (character) of argument")


def _sum_object(diagonal):
    integer_total = 0
    float_total = np.longdouble(0)
    complex_total = 0j
    saw_float = False
    saw_complex = False
    for value in diagonal:
        if isinstance(value, (str, np.str_)):
            raise ValueError("invalid 'type' (character) of argument")
        if isinstance(value, (bytes, np.bytes_, bytearray)):
            raise ValueError("invalid 'type' (raw) of argument")
        if isinstance(value, (list, tuple, dict)):
            raise ValueError("invalid 'type' (list) of argument")
        if isinstance(value, bool) or (isinstance(value, np.generic) and value.dtype.kind == "b"):
            integer_total += int(value)
        elif isinstance(value, (int, np.integer)):
            integer_total += int(value)
        elif isinstance(value, (float, np.floating)):
            saw_float = True
            float_total += np.longdouble(float(value))
        elif isinstance(value, (complex, np.complexfloating)):
            saw_complex = True
            complex_total += complex(value)
        else:
            raise ValueError("invalid 'type' (character) of argument")
    if saw_complex:
        return complex_total + integer_total + float(float_total)
    if saw_float:
        return float(float_total) + integer_total
    return _finish_integer(integer_total)


def _finish_integer(total):
    if _INT_MIN <= total <= _INT_MAX:
        return int(total)
    return float(total)
