"""Bernoulli numbers and polynomials."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.special_common import is_numeric_value, length_of, stop_unless
from pracma.special_poly import polyval
from pracma.special_zeta import zeta

_MISSING = object()


def bernoulli(n, x=_MISSING):
    stop_unless(length_of(n) == 1, "length(n) == 1 is not TRUE")
    number = float(np.asarray(n).reshape(-1)[0])
    stop_unless(math.floor(number) == math.ceil(number), "floor(n) == ceiling(n) is not TRUE")
    stop_unless(number >= 0, "n >= 0 is not TRUE")
    degree = int(number)
    if x is _MISSING:
        if degree == 0:
            return np.array([1.0])
        values = np.empty(degree + 1, dtype=float)
        values[0] = 1.0
        for index in range(1, degree + 1):
            values[index] = -index * float(np.asarray(zeta(1 - index)).reshape(-1)[0])
        values[1] = -0.5
        return values
    stop_unless(is_numeric_value(x), "is.numeric(x) is not TRUE")
    numbers = bernoulli(degree)
    choose = np.array([math.comb(degree, k) for k in range(degree + 1)], dtype=float)
    return np.asarray(polyval(choose * numbers, as_1d(x)), dtype=float).reshape(-1)
