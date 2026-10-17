"""Entrywise matrix norm, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def entrywise_norm(x, p):
    """Return the entrywise \\|x\\|_p norm of a numeric matrix or vector.

    Vectors are promoted to column matrices. A zero exponent raises
    ``exponent p is zero``. An infinite exponent delegates to
    ``maximum_norm`` on the original ``x``.
    """
    array = _raw_numeric_array(x)
    if np.isinf(p):
        return _maximum_norm(x)
    if p == 0:
        raise ValueError("exponent p is zero")
    xmat = _as_column_matrix(array, x)
    total = np.sum(np.abs(xmat) ** p)
    return float(total ** (1.0 / p))


def _maximum_norm(x):
    """``maximum.norm`` body until that export is translated."""
    array = _raw_numeric_array(x)
    if isinstance(x, np.ndarray) and x.ndim == 2:
        xmat = x
    elif _is_r_vector(array, x):
        raise NameError("name 'Xmat' is not defined")
    else:
        raise ValueError("argument is neither a matrix nor a vector")
    return float(np.max(np.abs(xmat)))


def _as_column_matrix(array, original):
    if isinstance(original, np.ndarray) and original.ndim == 2:
        return np.asarray(array, dtype=float)
    if _is_r_vector(array, original):
        return np.asarray(array, dtype=float).reshape(-1, 1)
    raise ValueError("argument x is neither vector nor matrix")


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
