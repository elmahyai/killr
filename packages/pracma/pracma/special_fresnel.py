"""Normalized Fresnel integrals."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.special_common import is_numeric_value

_EPS = np.finfo(float).eps


def _fresnel(x):
    if not is_numeric_value(x) or np.asarray(x).size != 1:
        raise PracmaError("Argument 'x' must be a numeric scalar.")
    x = float(np.asarray(x).reshape(-1)[0])
    xa = abs(x)
    px = math.pi * xa
    t = 0.5 * px * xa
    t2 = t * t
    fc = 0.0
    fs = 0.0
    if xa == 0.0:
        return fc, fs
    if xa < 2.5:
        r = xa
        fc = r
        for k in range(1, 51):
            r = -0.5 * r * (4.0 * k - 3.0) / k / (2.0 * k - 1.0) / (4.0 * k + 1.0) * t2
            fc = fc + r
            if abs(r) < abs(fc) * _EPS:
                break
        fs = xa * t / 3.0
        r = fs
        for k in range(1, 51):
            r = -0.5 * r * (4.0 * k - 1.0) / k / (2.0 * k + 1.0) / (4.0 * k + 3.0) * t2
            fs = fs + r
            if abs(r) < abs(fs) * _EPS:
                break
    elif xa < 4.5:
        m = math.trunc(42.0 + 1.75 * t)
        su = 0.0
        f1 = 0.0
        f0 = 1.0e-100
        for k in range(m, -1, -1):
            f = (2.0 * k + 3.0) * f0 / t - f1
            if k == math.trunc(k / 2.0) * 2:
                fc = fc + f
            else:
                fs = fs + f
            su = su + (2.0 * k + 1.0) * f * f
            f1 = f0
            f0 = f
        q = math.sqrt(su)
        fc = fc * xa / q
        fs = fs * xa / q
    else:
        r = 1.0
        f = 1.0
        for k in range(1, 21):
            r = -0.25 * r * (4.0 * k - 1.0) * (4.0 * k - 3.0) / t2
            f = f + r
        r = 1.0 / (px * xa)
        g = r
        for k in range(1, 13):
            r = -0.25 * r * (4.0 * k + 1.0) * (4.0 * k - 1.0) / t2
            g = g + r
        t0 = t - math.trunc(t / (2.0 * math.pi)) * 2.0 * math.pi
        fc = 0.5 + (f * math.sin(t0) - g * math.cos(t0)) / px
        fs = 0.5 - (f * math.cos(t0) + g * math.sin(t0)) / px
    if x < 0:
        fc = -fc
        fs = -fs
    return fc, fs


def fresnelS(x):
    if not is_numeric_value(x):
        raise PracmaError("Argument 'x' must be a numeric scalar.")
    values = as_1d(x)
    return np.array([_fresnel(float(item))[1] for item in values], dtype=float)


def fresnelC(x):
    if not is_numeric_value(x):
        raise PracmaError("Argument 'x' must be a numeric scalar.")
    values = as_1d(x)
    return np.array([_fresnel(float(item))[0] for item in values], dtype=float)
