"""Richardson extrapolation for a first derivative."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, is_r_vector

_EPS = float(np.finfo(float).eps)


def numderiv(f, x0, maxiter=16, h=0.5, *args, tol=_EPS, **kwargs):
    if r_scalar_bad(x0):
        raise PracmaError("Argument 'x0' must be a numeric scalar.")

    def fun(point):
        return f(point, *args, **kwargs)

    origin = float(np.asarray(x0, dtype=float).reshape(-1)[0])
    if np.asarray(fun(origin)).size != 1:
        raise PracmaError("Function 'f' must be a univariate function of one variable.")
    err = 1.0
    step = float(h)
    limit = int(maxiter)
    table = np.zeros((limit, limit))
    table[0, 0] = (float(fun(origin + step)) - float(fun(origin - step))) / (2.0 * step)
    j = 1
    while err > tol and j < limit:
        step = step / 2.0
        table[j, 0] = (float(fun(origin + step)) - float(fun(origin - step))) / (2.0 * step)
        for k in range(1, j + 1):
            table[j, k] = table[j, k - 1] + (table[j, k - 1] - table[j - 1, k - 1]) / (4.0 ** k - 1.0)
        err_new = 2.0 * abs(table[j, j] - table[j - 1, j - 1]) / (
            abs(table[j, j]) + abs(table[j - 1, j - 1]) + _EPS
        )
        if err_new >= err:
            break
        err = err_new
        j += 1
    if j >= limit:
        warnings.warn("Maximum number of iterations reached.", stacklevel=2)
    return {"df": float(table[j - 1, j - 1]), "rel.err": float(err), "niter": int(j)}


def r_scalar_bad(x0) -> bool:
    if not is_r_numeric(x0):
        return True
    return np.asarray(x0).size != 1


def numdiff(f, x, maxiter=16, h=0.5, *args, tol=_EPS, **kwargs):
    if not is_r_vector(x) or not is_r_numeric(x):
        raise PracmaError("Argument 'x' must be a numeric vector.")
    # The installed function passes machine epsilon, not the tol argument.
    values = np.asarray(x, dtype=float).reshape(-1)
    return np.array([
        numderiv(f, float(point), maxiter=maxiter, h=h, *args, tol=_EPS, **kwargs)["df"]
        for point in values
    ])
