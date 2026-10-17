"""N matrix (K + I) / 2, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.k_matrix import k_matrix

_MISSING = object()


def n_matrix(n=_MISSING):
    """Return the order ``n * n`` matrix ``(K + I) / 2`` for the commutation matrix ``K``.

    The argument must be an integer at least 2.
    """
    if n is _MISSING:
        raise ValueError("argument n is missing")
    n = _scalar_integer(n)
    size = n * n
    return (k_matrix(n) + np.eye(size, dtype=float)) / 2.0


def _scalar_integer(n):
    if isinstance(n, bool):
        raise ValueError("argument n is not numeric")
    if isinstance(n, np.ndarray):
        if n.ndim == 0:
            n = n.item()
        else:
            raise ValueError("argument n is not the proper data type")
    if isinstance(n, (list, tuple)):
        if len(n) != 1:
            raise ValueError("argument n is not a scalr number")
        n = n[0]
    if not isinstance(n, (int, float, np.integer, np.floating)):
        raise ValueError("argument n is not numeric")
    if isinstance(n, (float, np.floating)):
        number = float(n)
        if not np.isfinite(number):
            raise ValueError("argument n is not an integer")
        if number != int(number):
            raise ValueError("argument n is not an integer")
        number = int(number)
    else:
        number = int(n)
    if number < 2:
        raise ValueError("argument n is less than 2")
    return number
