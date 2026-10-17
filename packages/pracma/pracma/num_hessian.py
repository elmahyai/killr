"""Hessian, Hessian diagonal, Hessian-vector product, and Laplacian."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_fderiv import fderiv
from pracma.num_grad import grad
from pracma.num_helpers import is_r_numeric

_EPS = float(np.finfo(float).eps)


def _bind(f, args, kwargs):
    def fun(x):
        return f(x, *args, **kwargs)
    return fun


def _scalar(fun, point) -> float:
    return float(np.asarray(fun(point), dtype=float).reshape(-1)[0])


def hessian(f, x0, h=_EPS ** 0.25, *args, **kwargs):
    if not is_r_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric vector.")
    fun = _bind(f, args, kwargs)
    point = np.asarray(x0, dtype=float).reshape(-1)
    if np.asarray(fun(point)).size != 1:
        raise PracmaError("Function 'f' must be a univariate function of n variables.")
    step = float(h)
    if point.size == 1:
        return np.array([[float(np.asarray(fderiv(fun, point, n=2, h=step)).reshape(-1)[0])]])
    hess = np.full((point.size, point.size), np.nan)
    identity = np.eye(point.size) * step
    for i in range(point.size - 1):
        hi = identity[:, i]
        hess[i, i] = (_scalar(fun, point - hi) - 2 * _scalar(fun, point) + _scalar(fun, point + hi)) / step ** 2
        for j in range(i + 1, point.size):
            hj = identity[:, j]
            hess[i, j] = (
                _scalar(fun, point + hi + hj) - _scalar(fun, point + hi - hj)
                - _scalar(fun, point - hi + hj) + _scalar(fun, point - hi - hj)
            ) / (4.0 * step ** 2)
            hess[j, i] = hess[i, j]
    hi = identity[:, -1]
    hess[-1, -1] = (_scalar(fun, point - hi) - 2 * _scalar(fun, point) + _scalar(fun, point + hi)) / step ** 2
    return hess


def hessvec(f, x, v, csd=False, *args, **kwargs):
    if not is_r_numeric(x) or not is_r_numeric(v):
        raise PracmaError("Arguments 'x' and 'v' must be a numeric.")
    fun = _bind(f, args, kwargs)
    point = np.asarray(x, dtype=float).reshape(-1)
    direction = np.asarray(v, dtype=float).reshape(-1)
    if point.size < 2 or np.asarray(fun(point)).size != 1:
        raise PracmaError("Function 'f' must be univariate of 2 or more variables.")
    if direction.size != point.size:
        raise PracmaError("Vectors 'x' and 'v' must be of equal length.")
    step = _EPS ** 0.25
    radius = step / math_sqrt(direction)
    if csd:
        from pracma.num_complexstep import grad_csd
        product = (grad_csd(fun, point + radius * direction) - grad_csd(fun, point - radius * direction)) / (2.0 * radius)
    else:
        product = (grad(fun, point + radius * direction) - grad(fun, point - radius * direction)) / (2.0 * radius)
    return product


def math_sqrt(direction) -> float:
    return float(np.sqrt(np.sum(direction * direction)))


def hessdiag(f, x, *args, **kwargs):
    if not is_r_numeric(x):
        raise PracmaError("Arguments 'x' and 'v' must be a numeric.")
    fun = _bind(f, args, kwargs)
    point = np.asarray(x, dtype=float).reshape(-1)
    if point.size < 2 or np.asarray(fun(point)).size != 1:
        raise PracmaError("Function 'f' must be univariate of 2 or more variables.")
    step = _EPS ** 0.25
    shift = np.zeros(point.size)
    diagonal = np.zeros(point.size)
    center = _scalar(fun, point)
    for index in range(point.size):
        shift[index] = step
        diagonal[index] = (_scalar(fun, point + shift) - 2 * center + _scalar(fun, point - shift)) / step ** 2
        shift[index] = 0.0
    return diagonal


def laplacian(f, x0, h=_EPS ** 0.25, *args, **kwargs):
    if not is_r_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric vector.")
    fun = _bind(f, args, kwargs)
    point = np.asarray(x0, dtype=float).reshape(-1)
    step = float(h)
    shift = np.zeros(point.size)
    total = 0.0
    center = _scalar(fun, point)
    for index in range(point.size):
        shift[index] = step
        total += (_scalar(fun, point + shift) + _scalar(fun, point - shift) - 2 * center) / step ** 2
        shift[index] = 0.0
    return float(total)
