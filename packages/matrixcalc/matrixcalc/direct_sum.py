"""Direct sum of two arrays, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def direct_sum(x, y):
    """Return the block diagonal direct sum of two numeric vectors or matrices.

    Each vector is promoted to a column matrix, as R ``matrix(x)`` does.
    """
    a = _matrix_or_vector(x, "x")
    b = _matrix_or_vector(y, "y")
    top = np.hstack([a, np.zeros((a.shape[0], b.shape[1]), dtype=a.dtype)])
    bottom = np.hstack([np.zeros((b.shape[0], a.shape[1]), dtype=b.dtype), b])
    return np.vstack([top, bottom])


def _matrix_or_vector(value, name):
    if isinstance(value, np.ndarray):
        array = value
    elif isinstance(value, (list, tuple)):
        array = np.asarray(value)
    elif isinstance(value, (bool, np.bool_)):
        array = np.asarray([value], dtype=float)
    elif isinstance(value, (int, float, np.integer, np.floating)):
        array = np.asarray([value], dtype=float)
    else:
        raise ValueError(f"Argument {name} is not a matrix or vector")

    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError(f"Argument {name} is not a matrix or vector")

    if array.dtype == bool or np.issubdtype(array.dtype, np.integer):
        return array.astype(float, copy=False)
    return np.asarray(array, dtype=float)
