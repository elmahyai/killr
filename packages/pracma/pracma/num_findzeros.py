"""Roots and minima on a bracketed interval."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, r_optimize, r_uniroot

_EPS = float(np.finfo(float).eps)


def _interval(f, a, b, n, args, kwargs):
    if not is_r_numeric(a) or np.asarray(a).size != 1:
        raise PracmaError("is.numeric(a) is not TRUE" if not is_r_numeric(a) else "length(a) == 1 is not TRUE")
    if not is_r_numeric(b) or np.asarray(b).size != 1:
        raise PracmaError("is.numeric(b) is not TRUE" if not is_r_numeric(b) else "length(b) == 1 is not TRUE")
    if not is_r_numeric(n) or float(n) != math.floor(float(n)) or float(n) < 2:
        raise PracmaError("n >= 2 is not TRUE")
    left = float(np.asarray(a).reshape(-1)[0])
    right = float(np.asarray(b).reshape(-1)[0])
    if not left < right:
        raise PracmaError("Left interval border must be smaller than right one.")

    def fun(x):
        return np.asarray(f(x, *args, **kwargs), dtype=float)

    count = int(n)
    step = (right - left) / count
    grid = left + step * np.arange(count + 1)
    return fun, left, right, count, step, grid


def findzeros(f, a, b, n=100, tol=_EPS ** (2.0 / 3.0), *args, **kwargs):
    fun, left, right, count, step, grid = _interval(f, a, b, n, args, kwargs)
    values = fun(grid)
    roots = []
    sign = float(np.sign(fun(grid[0])))
    if abs(float(fun(grid[0]))) < tol:
        roots.append(float(grid[0]))
        sign = 0.0
    for i in range(1, count):
        current = float(np.sign(fun(grid[i])))
        if abs(float(fun(grid[i]))) < tol:
            roots.append(float(grid[i]))
            current = 0.0
        elif sign * current < 0:
            roots.append(r_uniroot(lambda t: float(fun(t)), float(grid[i - 1]), float(grid[i])))
        elif sign * current > 0:
            midpoint = (grid[i - 1] + grid[i]) / 2.0
            slope = (values[i] - values[i - 1]) / step
            if slope == 0:
                sign = current
                continue
            guess = midpoint - float(fun(midpoint)) / slope
            if grid[i - 1] < guess < grid[i]:
                if sign > 0:
                    place, objective = r_optimize(lambda t: float(fun(t)), float(grid[i - 1]), float(grid[i]), tol=tol)
                else:
                    place, objective = r_optimize(
                        lambda t: float(fun(t)), float(grid[i - 1]), float(grid[i]), maximum=True, tol=tol
                    )
                if abs(objective) < tol:
                    roots.append(place)
        sign = current
    if abs(float(fun(grid[count]))) < tol:
        roots.append(float(grid[count]))
    if not roots:
        return None
    return np.array(roots, dtype=float)


def findmins(f, a, b, n=100, tol=_EPS ** (2.0 / 3.0), *args, **kwargs):
    fun, _, _, count, _, grid = _interval(f, a, b, n, args, kwargs)
    places = []
    for i in range(1, count - 1):
        if (float(fun(grid[i])) - float(fun(grid[i - 1])) < 0) and (float(fun(grid[i + 1])) - float(fun(grid[i])) > 0):
            place, _ = r_optimize(lambda t: float(fun(t)), float(grid[i - 1]), float(grid[i + 1]))
            places.append(place)
    if not places:
        return None
    return np.array(places, dtype=float)
