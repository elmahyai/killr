"""Combinations in the order of the Fortran combin routine."""

from __future__ import annotations

import math
import warnings

import numpy as np


def _as_count(value, label):
    array = np.atleast_1d(np.asarray(value))
    if array.size != 1:
        warnings.warn(f"Using first element as {label}", stacklevel=3)
        array = array[:1]
    number = float(array[0])
    integer = int(math.trunc(number))
    if number != integer:
        warnings.warn(f"Coercing {label} to integer", stacklevel=3)
    return integer


def _odd(j):
    return j % 2 == 1


def combos(n, p):
    """All p-subsets of 1..n, one subset per column, in combin's order."""
    universe = _as_count(n, "n")
    width = _as_count(p, "p")
    if width > universe:
        raise ValueError("p is greater than n")
    count = int(math.comb(universe, width))
    table = np.zeros((width, count), dtype=int)
    if width == 0 or count == 0:
        return table
    m0 = universe - width
    t = width + 1
    k = 0
    j = 0
    c = [0] * (universe + 2)
    e = [0] * (universe + 2)
    last = [0] * (universe + 2)
    c[1] = 0
    while True:
        j += 1
        c[j] = j
        e[j] = j - 1
        if _odd(j):
            last[j] = m0 + j
        else:
            last[j] = j + 1
        if j == width:
            break
    table[:, 0] = c[1 : width + 1]
    if width < universe:
        while True:
            k += 1
            s = c[j]
            mj = m0 + j
            e[width + 1] = width
            if _odd(j):
                if c[j] == mj:
                    c[j] = c[j - 1] + 1
                    last[j + 1] = c[j] + 1
                else:
                    c[j] = c[j] + 1
            else:
                if c[j] == c[j - 1] + 1:
                    c[j] = mj
                else:
                    last[j + 1] = c[j]
                    c[j] = c[j] - 1
            if c[j] == last[j]:
                last[j] = s
                e[j + 1] = e[j]
                e[j] = j - 1
            if j < width and c[j] == mj:
                t = j
                j = e[t + 1]
                e[t + 1] = t
            else:
                if t == j:
                    t += 1
                if t < e[width + 1]:
                    j = t
                else:
                    j = e[width + 1]
            if k >= count:
                break
            table[:, k] = c[1 : width + 1]
            if j == 0:
                break
    return table
