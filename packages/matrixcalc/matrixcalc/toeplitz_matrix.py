"""Toeplitz matrix from a length 2n-1 vector, matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def toeplitz_matrix(n, x):
    """Return the order ``n`` Toeplitz matrix built from vector ``x``.

    ``x`` must have length ``2 * n - 1``. Entry ``(i, j)`` is ``x[(i - j) + n]`` in
    R's one-based indexing.
    """
    order = _validate_n(n)
    vector = _validate_x(x, order)
    i_idx, j_idx = np.indices((order, order))
    return vector[(i_idx - j_idx) + order - 1].astype(float, copy=False)


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
    expected = 2 * n - 1
    if isinstance(x, np.ndarray):
        if x.ndim != 1:
            raise ValueError("argument x is not a vector")
        vector = np.asarray(x, dtype=float)
    elif isinstance(x, (list, tuple)):
        vector = np.asarray(x, dtype=float)
    else:
        raise ValueError("argument x is not a vector")
    if vector.shape[0] != expected:
        raise ValueError("length of argument x is not comparable with n n")
    return vector
