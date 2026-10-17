"""Aitken acceleration of a fixed-point iteration."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric


def aitken(f, x0, nmax=12, tol=1e-8, *args, **kwargs):
    if not is_r_numeric(x0) or np.asarray(x0).size != 1:
        raise PracmaError("Argument 'x0' must be a numeric scalar.")

    def fun(x):
        return float(f(x, *args, **kwargs))

    x = float(np.asarray(x0).reshape(-1)[0])
    diff = 1 + tol
    niter = 0
    while diff > tol and niter <= nmax:
        gx = fun(x)
        ggx = fun(gx)
        xnew = (x * ggx - gx ** 2) / (ggx - 2 * gx + x)
        diff = abs(x - xnew)
        x = xnew
        niter += 1
    if niter > nmax:
        warnings.warn("Maximum number of iterations exceeded.", stacklevel=2)
    return float(x)
