"""Hadamard product of two arrays, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def hadamard_prod(x, y):
    """Return the element-wise Hadamard product of two numeric matrices or vectors.

    Vectors are promoted to column matrices. A vector ``y`` uses ``nrow = length(x)``
    in R, where ``length`` is the number of elements in ``x`` before promotion.
    """
    x_length = _length(x)
    a = _matrix_or_vector(x, "x")
    b = _matrix_or_vector(y, "y", vector_nrow=x_length)
    if a.shape[0] != b.shape[0]:
        raise ValueError("argumentx x and y do not have the same row order")
    if a.shape[1] != b.shape[1]:
        raise ValueError("arguments x and y do not have the same column order")
    return a * b


def _length(value):
    array = _raw_numeric_array(value, "x")
    if array.ndim == 0:
        return 1
    return int(array.size)


def _matrix_or_vector(value, name, vector_nrow=None):
    array = _raw_numeric_array(value, name)
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim == 1:
        nrow = array.size if vector_nrow is None else vector_nrow
        array = np.asarray(array, dtype=float).reshape(nrow, 1)
    elif array.ndim != 2:
        raise ValueError(f"Argument {name} is not a matrix or vector")

    if array.dtype == bool or np.issubdtype(array.dtype, np.integer):
        return array.astype(float, copy=False)
    return np.asarray(array, dtype=float)


def _raw_numeric_array(value, name):
    if isinstance(value, np.ndarray):
        array = value
    elif isinstance(value, (list, tuple)):
        array = np.asarray(value)
    elif isinstance(value, (bool, np.bool_)):
        array = np.asarray([value], dtype=float)
    elif isinstance(value, (int, float, np.integer, np.floating)):
        array = np.asarray([value], dtype=float)
    else:
        raise ValueError(f"argument {name} is not numeric")
    return array
