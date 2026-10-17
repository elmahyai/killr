"""One matrix norm, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def one_norm(x):
    """Return the 1-norm (maximum absolute column sum) of a numeric matrix or vector."""
    array = _raw_numeric_array(x)
    if isinstance(x, np.ndarray) and x.ndim == 2:
        xmat = array
    elif _is_r_vector(array, x):
        xmat = array.reshape(-1, 1)
    else:
        raise ValueError("argument x is neither a matrix nor a vector")

    col_sums = np.sum(np.abs(xmat), axis=0)
    if col_sums.size == 0:
        return float("-inf")
    return float(np.max(col_sums))


def _is_r_vector(array, original):
    if isinstance(original, np.ndarray):
        return original.ndim == 1
    if isinstance(original, (list, tuple)):
        return True
    if isinstance(original, (bool, int, float, np.bool_, np.integer, np.floating)):
        return array.ndim <= 1
    return array.ndim == 1


def _raw_numeric_array(value):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError("argument x is not numeric")
    if isinstance(value, np.ndarray):
        array = value
    elif isinstance(value, (list, tuple)):
        array = np.asarray(value)
    elif isinstance(value, (int, float, np.integer, np.floating)):
        array = np.asarray([value], dtype=float)
    else:
        raise ValueError("argument x is not numeric")

    if array.dtype == bool or array.dtype.kind == "b":
        raise ValueError("argument x is not numeric")
    if array.dtype.kind in "iu":
        array = array.astype(float, copy=False)
    elif array.dtype.kind == "f":
        array = np.asarray(array, dtype=float)
    else:
        raise ValueError("argument x is not numeric")
    return array
