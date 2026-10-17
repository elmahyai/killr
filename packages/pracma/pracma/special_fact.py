"""Factorial and double factorial."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_numeric_value, length_of, stop_unless


def fact(n):
    if not is_numeric_value(n):
        raise PracmaError("Argument 'n' must be a numeric vector or matrix.")
    array = np.asarray(n, dtype=float)
    shape = array.shape
    flat = np.floor(np.ravel(array, order="F"))
    out = np.ones(flat.shape, dtype=float)
    out[flat > 170] = np.inf
    out[flat < 0] = np.nan
    missing = np.isnan(flat)
    out[missing] = np.nan
    wanted = np.flatnonzero((flat > 0) & (flat <= 170) & ~missing)
    if wanted.size:
        limit = int(np.max(flat[wanted]))
        running = 1.0
        found = np.empty(wanted.size)
        targets = flat[wanted]
        for k in range(1, limit + 1):
            running *= k
            found[targets == k] = running
        out[wanted] = found
    if len(shape) >= 2:
        return np.reshape(out, shape, order="F")
    return out


def factorial2(n):
    stop_unless(is_numeric_value(n) or length_of(n) > 1, "is.numeric(n) || length(n) > 1 is not TRUE")
    if length_of(n) > 1:
        raise PracmaError("the condition has length > 1")
    number = math.floor(float(np.asarray(n).reshape(-1)[0]))
    if number > 170:
        return np.array([np.inf])
    if number < 0:
        return np.array([np.nan])
    if number == 0:
        return np.array([1.0])
    if number % 2 == 0:
        terms = np.arange(2, number + 1, 2, dtype=float)
    else:
        terms = np.arange(1, number + 1, 2, dtype=float)
    product = 1.0
    for term in terms:
        product *= float(term)
    return np.array([product])
