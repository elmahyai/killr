"""Trapezoidal integration."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError


def _vector(value, message):
    if value is None:
        return np.array([], dtype=float)
    array = np.asarray(value)
    if array.dtype == bool or array.dtype == np.bool_:
        raise PracmaError(message)
    if np.iscomplexobj(array):
        return np.array(array, dtype=complex).reshape(-1)
    if array.dtype == object or (array.size and not np.issubdtype(array.dtype, np.number)):
        raise PracmaError(message)
    return np.array(array, dtype=float).reshape(-1)


_TRAPZ_TYPE = "Arguments 'x' and 'y' must be real or complex vectors."
_CUM_TYPE = "Arguments 'x' and 'y' must be real or complex."


def trapz(x, y=None):
    if y is None:
        x = _vector(x, _TRAPZ_TYPE)
        if x.size == 0:
            return np.float64(0.0)
        y = x
        x = np.arange(1, y.size + 1, dtype=float)
    else:
        x = _vector(x, _TRAPZ_TYPE)
        y = _vector(y, _TRAPZ_TYPE)
        if x.size == 0 and y.size == 0:
            return np.float64(0.0)
    if x.size != y.size:
        raise PracmaError("Arguments 'x', 'y' must be vectors of the same length.")
    m = int(x.size)
    if m <= 1:
        return np.float64(0.0)
    xp = np.concatenate([x, x[::-1]])
    pad = np.zeros(m, dtype=y.dtype)
    yp = np.concatenate([pad, y[::-1]])
    n = 2 * m
    p1 = np.sum(xp[: n - 1] * yp[1:n]) + xp[n - 1] * yp[0]
    p2 = np.sum(xp[1:n] * yp[: n - 1]) + xp[0] * yp[n - 1]
    return 0.5 * (p1 - p2)


def cumtrapz(x, y=None):
    if y is None:
        x = _vector(x, _CUM_TYPE)
        if x.size == 0:
            return np.float64(0.0)
        y = x
        x = np.arange(1, y.size + 1, dtype=float)
    else:
        x = _vector(x, _CUM_TYPE)
    if x.size == 0:
        return np.float64(0.0)
    y_arr = np.asarray(y)
    if y_arr.dtype == bool or (y_arr.dtype == object) or (
        not np.iscomplexobj(y_arr) and y_arr.size and not np.issubdtype(y_arr.dtype, np.number)
    ):
        raise PracmaError("Arguments 'x' and 'y' must be real or complex.")
    if np.iscomplexobj(y_arr) or np.iscomplexobj(x):
        dtype = complex
    else:
        dtype = float
    x = np.array(x, dtype=dtype).reshape(-1, 1)
    m = x.shape[0]
    if y_arr.ndim == 1 or (y_arr.ndim == 0):
        y_mat = np.array(y_arr, dtype=dtype).reshape(-1, 1)
    elif y_arr.ndim == 2:
        y_mat = np.array(y_arr, dtype=dtype)
    else:
        raise PracmaError("Arguments 'x' and 'y' must be real or complex.")
    if y_mat.shape[0] != m:
        raise PracmaError("Arguments 'x' and 'y' are not compatible: nrow(y) != length(x).")
    if m < 2:
        raise PracmaError("subscript out of bounds")
    dt = np.diff(x.reshape(-1)) / 2.0
    increments = dt.reshape(-1, 1) * (y_mat[:-1, :] + y_mat[1:, :])
    ct = np.cumsum(increments, axis=0)
    return np.vstack([np.zeros((1, y_mat.shape[1]), dtype=dtype), ct])


def trapzfun(f, a, b, maxit=25, tol=1e-07, **kwargs):
    a = _finite_scalar(a, "a")
    b = _finite_scalar(b, "b")
    fun = _callable(f)

    def wrapped(x):
        return fun(x, **kwargs)

    if a == b:
        return {"area": np.float64(0.0), "iter": 0, "error": np.float64(0.0)}
    n = 1
    h = b - a
    total = h * (_as_float(wrapped(a)) + _as_float(wrapped(b))) / 2.0
    err = np.float64(np.nan)
    i = 0
    for i in range(1, int(maxit) + 1):
        mid = 0.0
        for j in range(n):
            mid = mid + _as_float(wrapped(a + (j + 0.5) * h))
        mid = h * mid
        total = (total + mid) / 2.0
        h = h / 2.0
        n = 2 * n
        err = abs(total - mid)
        if err < tol:
            break
    return {"value": np.float64(total), "iter": int(i), "rel.err": np.float64(err)}


def _finite_scalar(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    array = np.asarray(value)
    if array.size != 1 or np.iscomplexobj(array) or not np.issubdtype(array.dtype, np.number):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    number = float(array.reshape(-1)[0])
    if not math.isfinite(number):
        raise PracmaError(f"is.finite({name}) is not TRUE")
    return number


def _callable(fun):
    if not callable(fun):
        raise PracmaError("argument is not a function")
    return fun


def _as_float(value):
    array = np.asarray(value, dtype=float).reshape(-1)
    if array.size != 1:
        raise PracmaError("Function value must have length 1.")
    return float(array[0])
