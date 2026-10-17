"""perms and randperm from perms.R."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError


def _index_perms(count: int) -> np.ndarray:
    if count <= 1:
        return np.array([[1]], dtype=int)
    previous = _index_perms(count - 1)
    rows = previous.shape[0]
    table = np.zeros((count * rows, count), dtype=int)
    table[:rows, :] = np.column_stack([np.full(rows, count), previous])
    for value in range(count - 1, 0, -1):
        changed = previous.copy()
        changed[changed == value] = count
        start = rows * (count - value)
        stop = rows * (count - value + 1)
        table[start:stop, :] = np.column_stack([np.full(rows, value), changed])
    return table


def perms(a):
    if a is None or np.asarray(a).size == 0:
        return None
    values = np.asarray(a).reshape(-1)
    count = values.size
    if count == 1:
        return values.reshape(1, 1)
    table = _index_perms(count)
    flat = values[table.reshape(-1, order="F") - 1]
    return flat.reshape(table.shape, order="F")


def randperm(a, k=None):
    values = np.atleast_1d(np.asarray(a))
    count = values.size
    if count == 0 or values.reshape(-1)[0] == 0:
        return None
    population = values.reshape(-1)
    if count == 1:
        number = float(population[0])
        if math.floor(number) != math.ceil(number) or number < 1:
            raise PracmaError("Argument 'a' must be a positive integer.")
        count = int(number)
        population = np.arange(1, count + 1)
    if k is None:
        k = count
    take = int(k)
    if take > count:
        raise PracmaError("'k' must be smaller or equal to 'a' or length of 'a'.")
    choice = np.random.choice(count, size=take, replace=False)
    return np.asarray(population)[choice]
