"""List of E matrices, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def e_matrices(n):
    """Return nested E matrices built from the order ``n`` identity.

    Component ``result[i][j]`` is the ``n`` by ``n`` matrix ``e_i @ e_j.T`` where
    ``e_k`` is the ``k``th column of the identity. The argument must be an integer
    at least 2.
    """
    n = _scalar_integer(n)
    identity = np.eye(n, dtype=float)
    blocks = []
    for i in range(n):
        row = []
        for j in range(n):
            row.append(np.outer(identity[i], identity[j]))
        blocks.append(row)
    return blocks


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
