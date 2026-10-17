"""Combinations and a random combination."""

from __future__ import annotations

import numpy as np


def combs(a, m):
    values = np.asarray(a).reshape(-1, order="F")
    count = values.size
    degree = float(m)
    if count == 0 or degree <= 0:
        return None
    if degree >= count:
        return values.copy()
    if degree <= 1:
        return values.reshape(-1, 1)
    rows = []
    span = int(count - degree)
    for k in range(1, span + 1):
        tail = combs(values[k:], degree - 1)
        column = np.full((tail.shape[0], 1), values[k - 1], dtype=values.dtype)
        rows.append(np.column_stack([column, tail]))
    last_tail = np.asarray(combs(values[span + 1:], degree - 1)).reshape(-1)
    last = np.concatenate([np.array([values[span]], dtype=values.dtype), last_tail])
    return np.vstack(rows + [last.reshape(1, -1)])


def randcomb(a, m):
    values = np.asarray(a).reshape(-1, order="F")
    if values.size == 0:
        return None
    index = np.random.choice(values.size, size=int(m), replace=False)
    return values[index]
