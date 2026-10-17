"""Random matrices and samples from rand.R."""

from __future__ import annotations

import math
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.util_support import is_numeric, require


def _shape_pair(n, m):
    require(is_numeric(n), "is.numeric(n) is not TRUE")
    require(np.asarray(n).size <= 2, "length(n) <= 2 is not TRUE")
    require(is_numeric(m) if m is not None else True, "is.numeric(m) is not TRUE")
    rows = np.asarray(n, dtype=float).reshape(-1)
    if rows.size == 2:
        return None
    if m is None:
        cols = rows
    else:
        cols = np.asarray(m, dtype=float).reshape(-1)
    return math.floor(float(rows[0])), math.floor(float(cols[0]))


def _empty_or(rows, cols, draw):
    if rows <= 0 or cols <= 0:
        return np.full((0, 0), np.nan)
    return draw((rows, cols))


def rand(n=1, m=None):
    pair = _shape_pair(n, m if m is not None else n)
    if pair is None:
        values = np.asarray(n, dtype=float).reshape(-1)
        return rand(values[0], values[1])
    rows, cols = pair
    return _empty_or(rows, cols, np.random.random)


def randn(n=1, m=None):
    pair = _shape_pair(n, m if m is not None else n)
    if pair is None:
        values = np.asarray(n, dtype=float).reshape(-1)
        return randn(values[0], values[1])
    rows, cols = pair
    return _empty_or(rows, cols, lambda shape: np.random.standard_normal(shape))


def randi(imax, n=1, m=None):
    require(is_numeric(n), "is.numeric(n) is not TRUE")
    require(np.asarray(n).size == 1, "length(n) == 1 is not TRUE")
    if m is None:
        m = n
    require(is_numeric(m), "is.numeric(m) is not TRUE")
    require(np.asarray(m).size == 1, "length(m) == 1 is not TRUE")
    limits = np.asarray(imax, dtype=float).reshape(-1)
    if limits.size == 1:
        low, high = 1.0, float(limits[0])
    elif limits.size == 2:
        low, high = float(limits[0]), float(limits[1])
    else:
        raise PracmaError("Argument 'imax' must be a scalar or have two elements.")
    if low > high:
        raise PracmaError("Argument 'imax' must be greater than or equal to 'imin'.")
    rows = math.floor(float(np.asarray(n).reshape(-1)[0]))
    cols = math.floor(float(np.asarray(m).reshape(-1)[0]))
    if rows <= 0 or cols <= 0:
        return np.full((0, 0), np.nan)
    # R's colon on the documented integer limits.
    start = int(low) if float(low).is_integer() else low
    stop = int(high) if float(high).is_integer() else high
    if isinstance(start, int) and isinstance(stop, int):
        return np.random.randint(start, stop + 1, size=(rows, cols))
    population = np.arange(start, stop + 1)
    choice = np.random.choice(population, size=rows * cols, replace=True)
    return choice.reshape((rows, cols), order="F")


def rands(n=1, N=1, r=1):
    if n < 1 or N < 1 or r < 0:
        return None
    draws = randn(n, N + 1)
    norms = np.sqrt(np.sum(draws**2, axis=1))
    return r * draws / norms.reshape(-1, 1)


def randp(n=1, r=1):
    if n < 1 or r < 0:
        return None
    count = int(np.floor(n)) if float(n) == int(n) else int(n)
    x = np.random.standard_normal(count)
    y = np.random.standard_normal(count)
    scale = r * np.sqrt(np.random.random(count) / (x**2 + y**2))
    return np.column_stack([scale * x, scale * y])


def randsample(n, k, w=None, replacement=False):
    require(is_numeric(n), "is.numeric(n) is not TRUE")
    require(is_numeric(k), "is.numeric(k) is not TRUE")
    values = np.asarray(n, dtype=float).reshape(-1)
    if values.size == 1:
        population = np.arange(1, math.floor(float(values[0])) + 1, dtype=float)
    else:
        population = values.copy()
    take = int(np.asarray(k, dtype=float).reshape(-1)[0])
    if take > population.size and not replacement:
        warnings.warn("k > n or length(n): replacement will be set to TRUE.")
        replacement = True
    probabilities = None
    if w is not None and is_numeric(w):
        replacement = True
        weights = np.asarray(w, dtype=float).reshape(-1)
        if population.size != weights.size:
            raise PracmaError("Weights vector 'w' must have the same length as 'n'.")
        total = float(np.sum(weights))
        probabilities = None if total == 0 else weights / total
    choice = np.random.choice(population.size, size=take, replace=replacement, p=probabilities)
    return population[choice]
