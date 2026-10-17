"""Stirling matrix of second-kind numbers, matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def stirling_matrix(n):
    """Return the order ``n + 1`` Stirling matrix.

    The matrix is lower triangular and holds Stirling numbers of the second kind.
    The argument must be a positive numeric scalar.
    """
    n = _scalar_n(n)
    if n == 1:
        return S  # noqa: F821
    nm1 = n - 1
    np1 = n + 1
    matrix = np.zeros((np1, np1), dtype=float)
    for i in range(n + 1):
        matrix[i, i] = 1.0
    for j in range(n + 1):
        matrix[0, j] = 0.0
        matrix[j, 0] = 0.0
    for i in range(1, nm1 + 1):
        for j in range(1, i + 1):
            matrix[i + 1, j] = matrix[i, j - 1] + j * matrix[i, j]
    matrix[0, 0] = 1.0
    return matrix


def _scalar_n(n):
    if isinstance(n, bool):
        raise ValueError("argument n is not numeric")
    if isinstance(n, np.ndarray):
        if n.ndim == 0:
            n = n.item()
        else:
            raise ValueError("argument n is not of the proper data type")
    if isinstance(n, (list, tuple)):
        if len(n) != 1:
            raise ValueError("argument n is not a scalar integer")
        n = n[0]
    if not isinstance(n, (int, float, np.integer, np.floating)):
        raise ValueError("argument n is not numeric")
    if isinstance(n, (float, np.floating)):
        number = float(n)
        if not np.isfinite(number):
            raise ValueError("argument n is not numeric")
        number = int(number) if number == int(number) else number
    else:
        number = int(n)
    if number < 1:
        raise ValueError("arguemtn n is less than 1")
    return int(number)
