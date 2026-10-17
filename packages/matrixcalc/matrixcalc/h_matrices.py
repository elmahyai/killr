"""List of H matrices for commutation-matrix construction, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np


def h_matrices(r, c=None):
    """Return a nested list of ``r`` by ``c`` H matrices.

    Component ``(i, j)`` is the outer product of row ``i`` of the order ``r``
    identity matrix and row ``j`` of the order ``c`` identity matrix.
    When ``c`` is omitted it defaults to ``r``.
    """
    if c is None:
        c = r
    r = _scalar_integer(r, "r")
    c = _scalar_integer(c, "c")
    ir = np.eye(r, dtype=float)
    ic = np.eye(c, dtype=float)
    result = []
    for i in range(r):
        row = []
        for j in range(c):
            row.append(np.outer(ir[i], ic[j]))
        result.append(row)
    return result


def _scalar_integer(value, name):
    if isinstance(value, bool):
        raise ValueError(f"argument {name} is not numeric")
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            value = value.item()
        else:
            raise ValueError(f"argument {name} is not the proper data type")
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError(f"argument {name} is not a scalr number")
        value = value[0]
    if not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"argument {name} is not numeric")
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise ValueError(f"argument {name} is not an integer")
        if number != int(number):
            raise ValueError(f"argument {name} is not an integer")
        number = int(number)
    else:
        number = int(value)
    if number < 2:
        raise ValueError(f"argument {name} is less than 2")
    return number
