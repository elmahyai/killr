"""Symmetric Pascal matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import math

import numpy as np

from matrixcalc.pascal_matrix import _positive_integer


def symmetric_pascal_matrix(n):
    """Return the order ``n`` symmetric Pascal matrix.

    The argument must be a positive integer.
    """
    order = _positive_integer(n)
    nm1 = order - 1
    values = [1.0] * nm1
    for i in range(1, nm1 + 1):
        for j in range(1, nm1 + 1):
            values.append(_n_over_r(i + j, j))
    body = np.asarray(values, dtype=float).reshape(order, nm1, order="C")
    return np.column_stack([np.ones(order, dtype=float), body])


def _n_over_r(n, r):
    return math.prod(range(1, n + 1)) / (
        math.prod(range(1, n - r + 1)) * math.prod(range(1, r + 1))
    )
