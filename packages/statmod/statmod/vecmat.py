"""Multiply matrix rows by a vector.

Translated from statmod 1.5.2 ``vecmat`` in ``R/matvec.R``.
"""

from __future__ import annotations

import numpy as np


def vecmat(v, M):
    """Return ``diag(v) %*% M`` without forming ``diag(v)``."""
    v = np.asarray(v, dtype=float).reshape(-1)
    values = np.asarray(M, dtype=float)
    if values.ndim == 0:
        matrix = values.reshape(1, 1)
    elif values.ndim == 1:
        matrix = values.reshape(-1, 1)
    else:
        matrix = values
    if v.size != matrix.shape[0]:
        raise ValueError("vecmat: Dimensions do not match")
    return v.reshape(-1, 1) * matrix
