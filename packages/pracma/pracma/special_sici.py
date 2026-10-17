"""Sine and cosine integrals."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.special_common import is_numeric_value, stop_unless

_P2 = 1.570796326794897
_EL = 0.5772156649015329
_EPSI = 1.0e-15


def _sici(x):
    stop_unless(is_numeric_value(x), "is.numeric(x) is not TRUE")
    stop_unless(np.asarray(x).size == 1, "length(x) == 1 is not TRUE")
    x = float(np.asarray(x).reshape(-1)[0])
    x2 = x * x
    if x >= 0.0:
        sgnx = 1.0
    else:
        sgnx = -1.0
        x = sgnx * x
        x2 = x * x
    if x == 0.0:
        si = 0.0
        ci = -math.inf
    elif x <= 16.0:
        xr = -0.25 * x2
        ci = _EL + math.log(x) + xr
        for k in range(2, 41):
            xr = -0.5 * xr * (k - 1) / (k * k * (2 * k - 1)) * x2
            ci = ci + xr
            if abs(xr) < abs(ci) * _EPSI:
                break
        xr = x
        si = x
        for k in range(1, 41):
            xr = -0.5 * xr * (2 * k - 1) / k / (4 * k * k + 4 * k + 1) * x2
            si = si + xr
            if abs(xr) < abs(si) * _EPSI:
                break
    elif x < 32.0:
        m = math.floor(47.2 + 0.82 * x)
        bj = np.zeros(m + 1)
        xa1 = 0.0
        xa0 = 1e-100
        for k in range(m, 0, -1):
            xa = 4.0 * k * xa0 / x - xa1
            bj[k] = xa
            xa1 = xa0
            xa0 = xa
        xs = bj[1]
        for k in range(3, m + 1, 2):
            xs = xs + 2.0 * bj[k]
        bj[1] = bj[1] / xs
        for k in range(2, m + 1):
            bj[k] = bj[k] / xs
        xr = 1.0
        xg1 = bj[1]
        for k in range(2, m + 1):
            xr = 0.25 * xr * (2.0 * k - 3.0) ** 2 / ((k - 1) * (2 * k - 1) ** 2) * x
            xg1 = xg1 + bj[k] * xr
        xr = 1.0
        xg2 = bj[1]
        for k in range(2, m + 1):
            xr = 0.25 * xr * (2 * k - 5) ** 2 / ((k - 1) * (2 * k - 3) ** 2) * x
            xg2 = xg2 + bj[k] * xr
        xcs = math.cos(x / 2.0)
        xss = math.sin(x / 2.0)
        ci = _EL + math.log(x) - x * xss * xg1 + 2 * xcs * xg2 - 2 * xcs * xcs
        si = x * xcs * xg1 + 2 * xss * xg2 - math.sin(x)
    else:
        xr = 1.0
        xf = 1.0
        for k in range(1, 10):
            xr = -2.0 * xr * k * (2 * k - 1) / x2
            xf = xf + xr
        xr = 1.0 / x
        xg = xr
        for k in range(1, 9):
            xr = -2.0 * xr * (2 * k + 1) * k / x2
            xg = xg + xr
        ci = xf * math.sin(x) / x - xg * math.cos(x) / x
        si = _P2 - xf * math.cos(x) / x - xg * math.sin(x) / x
    return sgnx * si, ci


def Si(x):
    stop_unless(is_numeric_value(x), "is.numeric(x) is not TRUE")
    values = as_1d(x)
    return np.array([_sici(float(item))[0] for item in values], dtype=float)


def Ci(x):
    stop_unless(is_numeric_value(x), "is.numeric(x) is not TRUE")
    values = as_1d(x)
    return np.array([_sici(float(item))[1] for item in values], dtype=float)
