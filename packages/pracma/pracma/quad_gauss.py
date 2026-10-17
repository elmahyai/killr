"""Gauss-Legendre, Gauss-Hermite, Gauss-Laguerre, and a tensor product rule."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Diag


def gaussLegendre(n, a, b):
    a = _scalar(a, "a")
    b = _scalar(b, "b")
    n = _count(n)
    i = np.arange(1, n, dtype=float)
    d = i / np.sqrt(4.0 * i * i - 1.0)
    values, vectors = np.linalg.eigh(Diag(d, 1) + Diag(d, -1))
    order = np.argsort(values)
    x = values[order]
    first = vectors[0, order]
    w = 2.0 * first * first
    x = 0.5 * ((b - a) * x + a + b)
    w = -0.5 * (a - b) * w
    return {"x": np.asarray(x, dtype=float), "w": np.asarray(w, dtype=float)}


def gaussHermite(n):
    n = _count(n)
    i = np.arange(1, n, dtype=float)
    d = np.sqrt(i / 2.0)
    values, vectors = np.linalg.eigh(Diag(d, 1) + Diag(d, -1))
    order = np.argsort(values)
    x = values[order]
    w = math.sqrt(math.pi) * vectors[0, order] ** 2
    return {"x": np.asarray(x, dtype=float), "w": np.asarray(w, dtype=float)}


def gaussLaguerre(n, a=0):
    n = _count(n)
    alpha = _scalar(a, "a")
    if alpha < 0:
        raise PracmaError("a >= 0 is not TRUE")
    i = np.arange(1, n + 1, dtype=float)
    d = (2.0 * i - 1.0) + alpha
    off = np.sqrt(i[: n - 1] * (np.arange(1, n, dtype=float) + alpha))
    values, vectors = np.linalg.eigh(Diag(d) + Diag(off, 1) + Diag(off, -1))
    order = np.argsort(values)
    x = values[order]
    w = math.gamma(alpha + 1.0) * vectors[0, order] ** 2
    return {"x": np.asarray(x, dtype=float), "w": np.asarray(w, dtype=float)}


def quad2d(f, xa, xb, ya, yb, n=32, **kwargs):
    _scalar(xa, "xa")
    _scalar(xb, "xb")
    _scalar(ya, "ya")
    _scalar(yb, "yb")
    fun = _callable(f)

    def wrapped(x, y):
        return fun(x, y, **kwargs)

    cx = gaussLegendre(n, xa, xb)
    cy = gaussLegendre(n, ya, yb)
    grid_x, grid_y = _meshgrid(cx["x"], cy["x"])
    values = np.asarray(wrapped(grid_x, grid_y), dtype=float)
    total = cx["w"].reshape(1, -1) @ values @ cy["w"].reshape(-1, 1)
    return np.float64(total.reshape(-1)[0])


def _meshgrid(x, y):
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    columns = x.size
    rows = y.size
    grid_x = np.repeat(x, rows).reshape((rows, columns), order="F")
    grid_y = np.tile(y, columns).reshape((rows, columns), order="F")
    return grid_x, grid_y


def _count(n):
    number = _scalar(n, "n")
    if number < 2:
        raise PracmaError("n >= 2 is not TRUE")
    return int(np.trunc(number))


def _scalar(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    array = np.asarray(value)
    if array.size != 1 or np.iscomplexobj(array) or not np.issubdtype(array.dtype, np.number):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    return float(array.reshape(-1)[0])


def _callable(fun):
    if not callable(fun):
        raise PracmaError("argument is not a function")
    return fun
