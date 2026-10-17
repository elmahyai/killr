"""Real branches of Lambert's W function."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.special_common import is_numeric_value


def _halley(w0, x):
    return w0 - (w0 * math.exp(w0) - x) / (
        (w0 + 1) * math.exp(w0) - (w0 + 2) * (w0 * math.exp(w0) - x) / (2 * w0 + 2)
    )


def _lambert_wp_one(x):
    if x < -1.0 / math.e:
        return math.nan
    if x == -1.0 / math.e:
        return -1.0
    if x <= 1.0:
        eta = 2.0 + 2.0 * math.e * x
        root = math.sqrt(eta)
        f2 = 3 * math.sqrt(2) + 6 - (
            ((2237 + 1457 * math.sqrt(2)) * math.e - 4108 * math.sqrt(2) - 5764) * root
        ) / ((215 + 199 * math.sqrt(2)) * math.e - 430 * math.sqrt(2) - 796)
        f1 = (1 - 1 / math.sqrt(2)) * (f2 + math.sqrt(2))
        w0 = -1 + root / (1 + f1 * root / (f2 + root))
    else:
        w0 = math.log(6 * x / (5 * math.log(12 / 5 * (x / math.log(1 + 12 * x / 5)))))
    w1 = _halley(w0, x)
    while abs(w1 - w0) > 1e-15:
        w0 = w1
        w1 = _halley(w0, x)
    return w1


def _lambert_wn_one(x):
    if x < -math.exp(-1) or x >= 0:
        return math.nan
    if x == math.exp(-1):
        return -1.0
    m1 = 0.3361
    m2 = -0.0042
    m3 = -0.0201
    sigma = -1 - math.log(-x)
    w0 = -1 - sigma - 2 / m1 * (
        1
        - 1
        / (1 + (m1 * math.sqrt(sigma / 2)) / (1 + m2 * sigma * math.exp(m3 * math.sqrt(sigma))))
    )
    r = abs(x - w0 * math.exp(w0))
    while r > 1e-15:
        w1 = w0 - (w0 * math.exp(w0) - x) / (
            math.exp(w0) * (w0 + 1) - (w0 + 2) * (w0 * math.exp(w0) - x) / (2 * w0 + 2)
        )
        r = abs(x - w1 * math.exp(w1))
        w0 = w1
    return w0


def lambertWp(x):
    if not is_numeric_value(x):
        raise PracmaError("Argument 'x' must be a numeric (real) vector.")
    values = as_1d(x)
    return np.array([_lambert_wp_one(float(item)) for item in values], dtype=float)


def lambertWn(x):
    if not is_numeric_value(x):
        raise PracmaError("Argument 'x' must be a numeric (real) scalar.")
    values = as_1d(x)
    return np.array([_lambert_wn_one(float(item)) for item in values], dtype=float)
