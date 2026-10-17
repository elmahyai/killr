"""Multiply matrix columns by a vector.

Translated from statmod 1.5.2 ``matvec`` in ``R/matvec.R``.
"""

from __future__ import annotations

import numpy as np


def matvec(M, v):
    """Return ``M %*% diag(v)`` without forming ``diag(v)``."""
    v = np.asarray(v, dtype=float).reshape(-1)
    values = np.asarray(M, dtype=float)
    if values.ndim == 0:
        matrix = values.reshape(1, 1)
    elif values.ndim == 1:
        matrix = values.reshape(-1, 1)
    else:
        matrix = values
    if v.size != matrix.shape[1]:
        raise ValueError("matvec: Dimensions do not match")
    return matrix * v
