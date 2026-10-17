"""Angle conversion, spacing, powers, roots, and small scalar helpers."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d, is_numeric

_PI = math.pi
_EPS = np.finfo(float).eps
_XMIN = np.finfo(float).tiny


def deg2rad(deg):
    values = as_1d(deg)
    return values * (_PI / 180.0)


def rad2deg(rad):
    values = as_1d(rad)
    return values / (_PI / 180.0)


def linspace(x1, x2, n=100):
    if not is_numeric(x1) or not is_numeric(x2):
        raise PracmaError("x1 and x2 must be numeric scalars")
    start = float(np.asarray(x1).reshape(-1)[0])
    stop = float(np.asarray(x2).reshape(-1)[0])
    count = math.floor(float(n))
    if count <= 1:
        return np.array([stop])
    return np.linspace(start, stop, count)


def logspace(x1, x2, n=50):
    stop = float(np.asarray(x2).reshape(-1)[0])
    if stop == _PI:
        stop = math.log10(stop)
    return 10.0 ** linspace(x1, stop, n)


def logseq(x1, x2, n=100):
    start = math.log(abs(float(np.asarray(x1).reshape(-1)[0])))
    stop = math.log(abs(float(np.asarray(x2).reshape(-1)[0])))
    return np.exp(linspace(start, stop, n))


def nextpow2(x):
    if x is None:
        return np.array([])
    values = np.asarray(x)
    if values.size == 0:
        return np.array([])
    if not np.issubdtype(values.dtype, np.number):
        raise PracmaError("Argument 'x' must be a numeric/complex vector/matrix.")
    magnitudes = np.abs(values.astype(complex) if np.iscomplexobj(values) else values.astype(float))
    magnitudes = np.where(magnitudes == 0, 1.0, magnitudes)
    return np.ceil(np.log2(magnitudes)).astype(float)


def pow2(f, e=None):
    base = np.asarray(f)
    if not np.issubdtype(base.dtype, np.number):
        raise PracmaError("Argument 'f' must be numeric or complex.")
    if e is None:
        exponent = base.astype(float).reshape(-1)
        mantissa = np.ones(exponent.shape)
    else:
        exponent = np.asarray(e)
        if not np.issubdtype(exponent.dtype, np.number):
            raise PracmaError("Argument 'e' must be numeric or complex.")
        mantissa = np.real(base).astype(float).reshape(-1)
        exponent = np.real(exponent).astype(float).reshape(-1)
        if mantissa.size != exponent.size:
            raise PracmaError("Arguments 'e' and 'f' must be of same length.")
    return mantissa * np.power(2.0, exponent)


def hypot(x, y):
    left = np.asarray(x) if x is not None else np.array([])
    right = np.asarray(y) if y is not None else np.array([])
    if left.ndim == 2 and right.ndim == 2:
        raise PracmaError("'length = 2' in coercion to 'logical(1)'")
    if (left.size == 0 and right.size <= 1) or (right.size == 0 and left.size <= 1):
        return np.array([])
    if not np.issubdtype(left.dtype, np.number) or not np.issubdtype(right.dtype, np.number):
        raise PracmaError("Arguments 'x' and 'y' must be numeric or complex.")
    if (left.ndim == 1 and right.ndim == 2) or (left.ndim == 2 and right.ndim == 1):
        raise PracmaError("Arguments 'x' and 'y' must be of the same size.")
    left = np.abs(left.astype(float)).reshape(-1)
    right = np.abs(right.astype(float)).reshape(-1)
    if left.size == 1 and right.size > 1:
        left = np.repeat(left, right.size)
    elif right.size == 1 and left.size > 1:
        right = np.repeat(right, left.size)
    if left.size != right.size:
        raise PracmaError("Arguments 'x' and 'y' must be of the same size.")
    small = np.minimum(left, right)
    large = np.maximum(left, right)
    out = np.zeros(large.shape)
    mask = large != 0
    out[mask] = large[mask] * np.sqrt(1.0 + (small[mask] / large[mask]) ** 2)
    return out


def nthroot(x, n):
    values = as_1d(x)
    if n is None or float(n) <= 0 or math.ceil(float(n)) != math.floor(float(n)):
        raise PracmaError("Argument 'n' must be a positive integer.")
    power = int(float(n))
    finite = values[~np.isnan(values)]
    if np.any(finite < 0) and power % 2 == 0:
        raise PracmaError("If argument 'x' is negative, 'n' must be an odd integer.")
    sign = np.sign(values)
    sign = np.where(np.isnan(values), np.nan, sign)
    return sign * np.power(sign * values, 1.0 / power)


def eps(x=1.0):
    values = as_1d(x)
    magnitude = float(np.max(np.abs(values))) if values.size else 0.0
    if magnitude < _XMIN:
        return float(_XMIN)
    return float(2.0 ** math.floor(math.log2(magnitude)) * _EPS)


def sigmoid(x, a=1, b=0):
    if x is not None and np.asarray(x).size == 0:
        return np.array([])
    values = as_1d(x)
    scale = float(np.asarray(a).reshape(-1)[0])
    shift = float(np.asarray(b).reshape(-1)[0])
    return 1.0 / (1.0 + np.exp(-scale * (values - shift)))


def logit(x, a=1, b=0):
    if x is not None and np.asarray(x).size == 0:
        return np.array([])
    values = as_1d(x)
    scale = float(np.asarray(a).reshape(-1)[0])
    shift = float(np.asarray(b).reshape(-1)[0])
    outside = (values < 0.0) | (values > 1.0)
    clipped = values.copy()
    clipped[outside] = 0.5
    result = shift + np.log(clipped / (1.0 - clipped)) / scale
    result[outside] = np.nan
    return result


def humps(x=None):
    if x is None:
        x = np.arange(0.0, 1.0 + 1e-12, 0.05)
    values = as_1d(x)
    return 1.0 / ((values - 0.3) ** 2 + 0.01) + 1.0 / ((values - 0.9) ** 2 + 0.04) - 6.0


def sinc(x):
    values = as_1d(x)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.sin(_PI * values) / (_PI * values)


def psinc(x, n):
    values = as_1d(x)
    count = float(n)
    if math.floor(count) != math.ceil(count) or count < 1:
        raise PracmaError("Argument 'n' must be a positive integer.")
    return np.sin(values * count / 2.0) / count * np.sin(values / 2.0)


def _recycle(left, right):
    a = np.asarray(left, dtype=float).reshape(-1)
    b = np.asarray(right, dtype=float).reshape(-1)
    if a.size == 0 or b.size == 0:
        return a[:0], b[:0]
    width = max(a.size, b.size)
    return np.resize(a, width), np.resize(b, width)


def and_(left, right):
    a, b = _recycle(left, right)
    return ((a != 0) & (b != 0)).astype(float)


def or_(left, right):
    a, b = _recycle(left, right)
    return ((a != 0) | (b != 0)).astype(float)
