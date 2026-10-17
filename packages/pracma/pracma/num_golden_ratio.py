"""Golden-section search for a minimum."""

from __future__ import annotations

import math

import numpy as np


def golden_ratio(f, a, b, *args, maxiter=100, tol=float(np.finfo(float).eps) ** 0.5, **kwargs):
    def fun(x):
        return float(f(x, *args, **kwargs))

    phi = 1 - (math.sqrt(5) - 1) / 2
    left = float(a)
    right = float(b)
    x = np.array([left, left + phi * (right - left), right - phi * (right - left), right])
    y2 = fun(x[1])
    y3 = fun(x[2])
    n = 0
    while x[2] - x[1] > tol:
        n += 1
        if y3 > y2:
            x = np.array([x[0], x[0] + phi * (x[2] - x[0]), x[1], x[2]])
            y3 = y2
            y2 = fun(x[1])
        else:
            x = np.array([x[1], x[2], x[3] - phi * (x[3] - x[1]), x[3]])
            y2 = y3
            y3 = fun(x[2])
        if n >= maxiter:
            break
    xm = (x[1] + x[2]) / 2
    value = fun(xm)
    if abs(value) <= tol ** 2:
        value = 0.0
    return {"xmin": float(xm), "fmin": float(value), "iter": int(n), "estim.prec": float(abs(x[2] - x[1]))}
