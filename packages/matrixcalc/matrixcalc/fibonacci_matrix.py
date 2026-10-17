"""Order n + 1 Fibonacci matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def fibonacci_matrix(n):
    """Return the order ``n + 1`` Fibonacci matrix.

    Typical element ``(i, j)`` is ``f[i - j]`` when ``i >= j - 1``, else zero,
    for the Fibonacci sequence with ``f[0] = f[1] = 1``.
    The argument must be a positive integer.
    """
    n = _scalar_integer(n)
    np1 = n + 1
    np2 = n + 2
    sequence = np.zeros(np2, dtype=float)
    sequence[0] = 1.0
    sequence[1] = 1.0
    for index in range(2, np2):
        sequence[index] = sequence[index - 1] + sequence[index - 2]
    matrix = np.zeros((np1, np1), dtype=float)
    for row in range(np1):
        for col in range(np1):
            if row - col + 1 >= 0:
                matrix[row, col] = sequence[row - col + 1]
    return matrix


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
    if number < 1:
        raise ValueError("argument n is less than 2")
    return number
