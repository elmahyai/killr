"""Vandermonde matrix from a vector of nodes, matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def vandermonde_matrix(alpha, n):
    """Return an ``m`` by ``n`` Vandermonde matrix for vector ``alpha``.

    Column ``j`` holds ``alpha ** (j - 1)``; the first column is ones.
    """
    vector = _validate_alpha(alpha)
    m = vector.shape[0]
    ncol = int(n)
    matrix = np.zeros((m, ncol), dtype=float)
    if ncol >= 1:
        matrix[:, 0] = 1.0
    j = 2
    while j <= n:
        matrix[:, j - 1] = vector ** (j - 1)
        j += 1
    return matrix


def _validate_alpha(alpha):
    if isinstance(alpha, bool):
        raise ValueError("argument n is not a numeric vector")
    if isinstance(alpha, (int, float, np.integer, np.floating)):
        vector = np.asarray([alpha], dtype=float)
    elif isinstance(alpha, np.ndarray):
        if alpha.ndim == 0:
            vector = np.asarray([alpha.item()], dtype=float)
        elif alpha.ndim != 1:
            raise ValueError("argument alpha is not a vector")
        else:
            if not np.issubdtype(alpha.dtype, np.number):
                raise ValueError("argument n is not a numeric vector")
            vector = np.asarray(alpha, dtype=float)
    elif isinstance(alpha, (list, tuple)):
        if len(alpha) == 0:
            vector = np.asarray(alpha, dtype=float)
        elif not all(isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, bool) for x in alpha):
            raise ValueError("argument n is not a numeric vector")
        vector = np.asarray(alpha, dtype=float)
    else:
        raise ValueError("argument alpha is not a vector")
    if vector.dtype.kind not in "iuf":
        raise ValueError("argument n is not a numeric vector")
    return vector
