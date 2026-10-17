"""u vectors of an identity matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def u_vectors(n):
    """Build the order ``n * (n + 1) // 2`` identity and the index map ``k``.

    Returns a dict with ``k``, an order-``n`` matrix whose lower-triangle entries
    map ``(i, j)`` to a column in ``I``, and ``I``, the identity matrix. The argument
    must be an integer at least 2.
    """
    n = _scalar_integer(n)
    p = n * (n + 1) // 2
    k = np.zeros((n, n), dtype=float)
    for j in range(1, n + 1):
        for i in range(j, n + 1):
            k[i - 1, j - 1] = (j - 1) * n + i - 0.5 * j * (j - 1)
    identity = np.eye(p, dtype=float)
    return {"k": k, "I": identity}


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
