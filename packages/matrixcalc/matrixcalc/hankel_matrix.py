"""Hankel matrix from a circularly shifted vector, matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def hankel_matrix(n, x):
    """Return an order ``n`` Hankel matrix built from vector ``x``.

    Each row after the first is a left circular shift of the previous row's
    source vector; row ``i`` uses the first ``n`` entries of the shifted vector.
    """
    n = _validate_n(n)
    y = _validate_x(x, n)
    m = y.shape[0]
    matrix = np.zeros((n, n), dtype=float)
    matrix[0, :] = y[:n]
    for row in range(1, n):
        y = np.concatenate((y[1:m], y[:1]))
        matrix[row, :] = y[:n]
    return matrix


def _validate_n(n):
    if isinstance(n, bool):
        raise ValueError("argument n is not numeric")
    if isinstance(n, np.ndarray):
        if n.ndim == 0:
            n = n.item()
        else:
            raise ValueError("argument n is not numeric")
    if isinstance(n, (list, tuple)):
        raise ValueError("argument n is not numeric")
    if not isinstance(n, (int, float, np.integer, np.floating)):
        raise ValueError("argument n is not numeric")
    if isinstance(n, (float, np.floating)):
        number = float(n)
        if not np.isfinite(number) or number != int(number):
            raise ValueError("argument n ix not an integer")
        number = int(number)
    else:
        number = int(n)
    if number < 2:
        raise ValueError("argument n is less than 2")
    return number


def _validate_x(x, n):
    if isinstance(x, np.ndarray):
        if x.ndim != 1:
            raise ValueError("argument x is not a vector")
        vector = np.asarray(x, dtype=float)
    elif isinstance(x, (list, tuple)):
        vector = np.asarray(x, dtype=float)
    else:
        raise ValueError("argument x is not a vector")
    if vector.shape[0] < n:
        raise ValueError("length of argument x is less than n")
    return vector
