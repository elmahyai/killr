"""Hilbert matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def hilbert_matrix(n):
    """Return the order ``n`` Hilbert matrix.

    Element ``(i, j)`` is ``1 / (i + j - 1)`` with one-based indices.
    The argument must be an integer at least 2.
    """
    n = _integer_dimension(n)
    rows = np.arange(n, dtype=float)
    cols = np.arange(1, n + 1, dtype=float)
    return 1.0 / np.add.outer(rows, cols)


def _integer_dimension(value):
    if isinstance(value, bool):
        raise ValueError("argument n is not an integer")
    if isinstance(value, (int, np.integer)):
        number = int(value)
    elif isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number) or number != int(number):
            raise ValueError("argument n is not an integer")
        number = int(number)
    else:
        raise ValueError("argument n is not an integer")
    if number < 2:
        raise ValueError("argument n is less than 2")
    return number
