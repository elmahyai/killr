"""Romberg arc length of a vector-valued curve."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric


def arclength(f, a, b, nmax=20, tol=1e-05, *args, **kwargs):
    if not is_r_numeric(a) or np.asarray(a).size != 1:
        raise PracmaError("is.numeric(a) is not TRUE" if not is_r_numeric(a) else "length(a) == 1 is not TRUE")
    if not is_r_numeric(b) or np.asarray(b).size != 1:
        raise PracmaError("is.numeric(b) is not TRUE" if not is_r_numeric(b) else "length(b) == 1 is not TRUE")

    def fun(point):
        return np.asarray(f(point, *args, **kwargs), dtype=float).reshape(-1)

    left = float(np.asarray(a).reshape(-1)[0])
    right = float(np.asarray(b).reshape(-1)[0])
    if abs(right - left) < tol:
        return {"length": 0.0, "niter": 0, "rel.err": float(tol)}
    fa = fun(left)
    fb = fun(right)
    m = fa.size
    if m < 2:
        raise PracmaError("Argument 'f' must be a parametrized function.")
    if fun(np.array([left, right])).size != 2 * m:
        raise PracmaError("Argument 'f' must be a vectorized function.")
    limit = int(nmax)
    table = np.zeros((limit, limit))
    table[0, 0] = float(np.sqrt(np.sum((fb - fa) ** 2)))
    i = 0
    for i in range(1, limit):
        count = 2 ** i + 1
        abscissa = np.linspace(left, right, count)
        values = fun(abscissa)
        points = values.reshape((-1, m), order="F")
        steps = np.diff(points, axis=0)
        table[i, 0] = float(np.sum(np.sqrt(np.sum(steps * steps, axis=1))))
        for j in range(i):
            power = 4.0 ** (j + 1)
            table[i, j + 1] = (power * table[i, j] - table[i - 1, j]) / (power - 1.0)
        if abs(table[i, i] - table[i - 1, i - 1]) < tol and i > 3:
            break
    error = abs(table[i, i] - table[i - 1, i - 1]) if i > 0 else tol
    return {"length": float(table[i, i]), "niter": int(i + 1), "rel.err": float(error)}
