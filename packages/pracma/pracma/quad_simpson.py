"""Simpson integration on a line and on a rectangle."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.elementary import linspace


def simpson(f, a, b, n=100, **kwargs):
    count = float(n)
    if count % 2 != 0:
        raise PracmaError("n must be even for Simpson's rule")
    panels = int(count)
    h = (float(b) - float(a)) / count
    x = linspace(a, b, panels + 1)
    y = _apply(f, x, kwargs)
    weights = np.tile(np.array([4.0, 2.0]), panels // 2)
    weights = np.concatenate([np.array([1.0]), weights])
    weights[-1] = 1.0
    return np.float64((h / 3.0) * np.sum(weights * y))


def simpson2d(f, xa, xb, ya, yb, nx=128, ny=128, **kwargs):
    _scalar(xa, "xa")
    _scalar(xb, "xb")
    _scalar(ya, "ya")
    _scalar(yb, "yb")
    fun = _callable(f)

    def wrapped(x, y):
        return fun(x, y, **kwargs)

    nx = int(math.floor(float(nx)))
    ny = int(math.floor(float(ny)))
    if nx % 2 != 0:
        nx = nx + 1
    if ny % 2 != 0:
        ny = ny + 1
    hx = (float(xb) - float(xa)) / nx
    hy = (float(yb) - float(ya)) / ny
    xg = _seq_by(float(xa), float(xb), hx)
    yg = _seq_by(float(ya), float(yb), hy)
    grid_y, grid_x = _meshgrid(yg, xg)
    values = np.asarray(wrapped(grid_x, grid_y), dtype=float)
    s1 = values[0, 0] + values[0, ny] + values[nx, 0] + values[nx, ny]
    ixo = _seq_index(2, nx, 2)
    ixe = _seq_index(3, nx - 1, 2)
    iyo = _seq_index(2, ny, 2)
    iye = _seq_index(3, ny - 1, 2)
    s2 = 2.0 * (
        _sum_index(values, np.array([0]), iye)
        + _sum_index(values, np.array([nx]), iye)
        + _sum_index(values, ixe, np.array([0]))
        + _sum_index(values, ixe, np.array([ny]))
    )
    s3 = 4.0 * (
        _sum_index(values, np.array([0]), iyo)
        + _sum_index(values, np.array([nx]), iyo)
        + _sum_index(values, ixo, np.array([0]))
        + _sum_index(values, ixo, np.array([ny]))
    )
    s4 = 16.0 * np.sum(values[np.ix_(ixo, iyo)]) + 4.0 * np.sum(values[np.ix_(ixe, iye)])
    s5 = 8.0 * np.sum(values[np.ix_(ixe, iyo)]) + 8.0 * np.sum(values[np.ix_(ixo, iye)])
    return np.float64(hx * hy * (s1 + s2 + s3 + s4 + s5) / 9.0)


def _sum_index(values, rows, cols):
    if rows.size == 0 or cols.size == 0:
        return 0.0
    return float(np.sum(values[np.ix_(rows, cols)]))


def _seq_index(start, stop, step):
    return _seq_by(start, stop, step).astype(int) - 1


def _seq_by(start, stop, step):
    start = float(start)
    stop = float(stop)
    step = float(step)
    if step == 0 or (stop - start) / step < 0:
        raise PracmaError("wrong sign in 'by' argument")
    count = int(math.floor((stop - start) / step + 1e-7))
    values = start + np.arange(count + 1, dtype=float) * step
    if step > 0:
        values = values[values <= stop]
    else:
        values = values[values >= stop]
    return values


def _meshgrid(x, y):
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    columns = x.size
    rows = y.size
    grid_x = np.repeat(x, rows).reshape((rows, columns), order="F")
    grid_y = np.tile(y, columns).reshape((rows, columns), order="F")
    return grid_x, grid_y


def _apply(f, x, kwargs):
    fun = _callable(f)
    values = np.asarray(fun(x, **kwargs), dtype=float).reshape(-1)
    return values


def _callable(fun):
    if not callable(fun):
        raise PracmaError("argument is not a function")
    return fun


def _scalar(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    array = np.asarray(value)
    if array.size != 1 or np.iscomplexobj(array) or not np.issubdtype(array.dtype, np.number):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    return float(array.reshape(-1)[0])
