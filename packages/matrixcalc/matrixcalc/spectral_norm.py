"""Spectral matrix norm, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.frobenius_norm import frobenius_norm


def spectral_norm(x):
    """Return the spectral (operator 2-) norm of a numeric matrix or vector.

    For a vector this is the Euclidean length. For a matrix, R forms ``t(x) %*%
    x``, takes the largest eigenvalue from ``eigen``, and returns its square
    root.
    """
    array = _raw_numeric_array(x)
    if _is_r_vector(array, x):
        return frobenius_norm(x)

    if isinstance(x, np.ndarray) and x.ndim == 2:
        xmat = np.asarray(array, dtype=float)
    else:
        raise ValueError("argument x is not a matrix")

    gram = xmat.T @ xmat
    eigenvalues = np.linalg.eig(gram)[0]
    lambda_a = np.sort(np.real(eigenvalues))[::-1]
    max_lambda = float(lambda_a[0])
    if max_lambda < 0:
        raise ValueError("t(x) %*% x is negative definite")
    return float(np.sqrt(max_lambda))


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
