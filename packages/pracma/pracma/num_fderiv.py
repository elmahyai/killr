"""Finite-difference derivatives."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, match_arg, r_colon, r_length

_EPS = float(np.finfo(float).eps)


def _choose_row(order):
    signs = (-1.0) ** np.arange(order + 1)
    binomials = np.array([math.comb(order, k) for k in range(order + 1)], dtype=float)
    return signs * binomials


def fderiv(f, x, n=1, h=0, method="central", *args, **kwargs):
    if r_length(x) == 0:
        return None
    if not is_r_numeric(x):
        raise PracmaError("Argument 'x' must be a number or a numeric vector.")
    order = math.floor(float(n))
    if order < 0:
        raise PracmaError("The order of the derivative, 'n', can only be between 0 and 8.")
    if order > 8:
        import warnings
        warnings.warn("Numerical derivatives of order 'n > 8' will be very inexact.", stacklevel=2)
    method = match_arg(method, ("central", "forward", "backward"))

    def fun(point):
        return np.asarray(f(point, *args, **kwargs), dtype=float)

    abscissa = np.asarray(x, dtype=float)
    values = fun(abscissa)
    if values.size != abscissa.size:
        raise PracmaError("Function 'f' must first be vectorized: Vectorize(f).")
    if order == 0:
        return fun(abscissa)
    step = float(h)
    if step == 0:
        step = _EPS ** (1.0 / (order + 2))

    if method == "central":
        if order == 1:
            derivative = (fun(abscissa + step) - fun(abscissa - step)) / (2.0 * step)
        elif order == 2:
            derivative = (fun(abscissa + step) - 2.0 * fun(abscissa) + fun(abscissa - step)) / step ** 2
        elif order == 3:
            derivative = (
                fun(abscissa + 2 * step) - 2 * fun(abscissa + step)
                + 2 * fun(abscissa - step) - fun(abscissa - 2 * step)
            ) / (2.0 * step ** 3)
        elif order == 4:
            derivative = (
                fun(abscissa + 2 * step) - 4 * fun(abscissa + step) + 6 * fun(abscissa)
                - 4 * fun(abscissa - step) + fun(abscissa - 2 * step)
            ) / step ** 4
        else:
            offsets = r_colon(order / 2.0, -order / 2.0) * step
            derivative = float(np.sum(_choose_row(order) * fun(offsets))) / step ** order
    elif method == "forward":
        if order == 1:
            derivative = (-fun(abscissa + 2 * step) + 4 * fun(abscissa + step) - 3 * fun(abscissa)) / (2.0 * step)
        elif order == 2:
            derivative = (
                -fun(abscissa + 3 * step) + 4 * fun(abscissa + 2 * step)
                - 5 * fun(abscissa + step) + 2 * fun(abscissa)
            ) / step ** 2
        elif order == 3:
            derivative = (
                -3 * fun(abscissa + 4 * step) + 14 * fun(abscissa + 3 * step)
                - 24 * fun(abscissa + 2 * step) + 18 * fun(abscissa + step) - 5 * fun(abscissa)
            ) / (2.0 * step ** 3)
        elif order == 4:
            derivative = (
                -2 * fun(abscissa + 5 * step) + 11 * fun(abscissa + 4 * step)
                - 24 * fun(abscissa + 3 * step) + 26 * fun(abscissa + 2 * step)
                - 14 * fun(abscissa + step) + 3 * fun(abscissa)
            ) / step ** 4
        else:
            offsets = r_colon(order, 0) * step
            derivative = float(np.sum(_choose_row(order) * fun(offsets))) / step ** order
    else:
        if order == 1:
            derivative = (3 * fun(abscissa) - 4 * fun(abscissa - step) + fun(abscissa - 2 * step)) / (2.0 * step)
        elif order == 2:
            derivative = (
                2 * fun(abscissa) - 5 * fun(abscissa - step)
                + 4 * fun(abscissa - 2 * step) - fun(abscissa - 3 * step)
            ) / step ** 2
        elif order == 3:
            derivative = (
                5 * fun(abscissa) - 18 * fun(abscissa - step) + 24 * fun(abscissa - 2 * step)
                - 14 * fun(abscissa - 3 * step) + 3 * fun(abscissa - 4 * step)
            ) / (2.0 * step ** 3)
        elif order == 4:
            derivative = (
                3 * fun(abscissa) - 14 * fun(abscissa - step) + 26 * fun(abscissa - 2 * step)
                - 24 * fun(abscissa - 3 * step) + 11 * fun(abscissa - 4 * step)
                - 2 * fun(abscissa - 5 * step)
            ) / step ** 4
        else:
            offsets = r_colon(0, -order) * step
            derivative = float(np.sum(_choose_row(order) * fun(offsets))) / step ** order
    return derivative
