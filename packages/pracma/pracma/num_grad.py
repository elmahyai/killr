"""Numerical gradient and Jacobian."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, r_length

_EPS = float(np.finfo(float).eps)


def grad(f, x0, heps=_EPS ** (1.0 / 3.0), *args, **kwargs):
    if not is_r_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric value.")

    def fun(x):
        return f(x, *args, **kwargs)

    point = np.asarray(x0, dtype=float).reshape(-1)
    if np.asarray(fun(point)).size != 1:
        raise PracmaError("Function 'f' must be a univariate function of 2 variables.")
    step = np.zeros(point.size)
    slope = np.zeros(point.size)
    for index in range(point.size):
        step[index] = heps
        slope[index] = (float(np.asarray(fun(point + step)).reshape(-1)[0])
                        - float(np.asarray(fun(point - step)).reshape(-1)[0])) / (2.0 * heps)
        step[index] = 0.0
    return slope


def jacobian(f, x0, heps=_EPS ** (1.0 / 3.0), *args, **kwargs):
    if not is_r_numeric(x0) or r_length(x0) == 0:
        raise PracmaError("Argument 'x' must be a non-empty numeric vector.")

    def fun(x):
        return np.asarray(f(x, *args, **kwargs), dtype=float).reshape(-1)

    point = np.asarray(x0, dtype=float).reshape(-1)
    rows = fun(point).size
    columns = point.size
    jac = np.full((rows, columns), np.nan)
    step = np.zeros(columns)
    for index in range(columns):
        step[index] = heps
        jac[:, index] = (fun(point + step) - fun(point - step)) / (2.0 * heps)
        step[index] = 0.0
    return jac
