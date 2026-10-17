"""Trigonometric regression."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric


def trigPoly(x, m):
    if not is_r_numeric(x):
        raise PracmaError("is.numeric(x) is not TRUE")
    if not is_r_numeric(m) or np.asarray(m).size != 1 or float(np.asarray(m).reshape(-1)[0]) < 0:
        raise PracmaError("is.numeric(m) is not TRUE" if not is_r_numeric(m) else "m >= 0 is not TRUE")
    degree = int(np.asarray(m).reshape(-1)[0])
    values = np.asarray(x, dtype=float).reshape(-1)
    if degree == 0:
        return {"a0": float(np.mean(values)), "a": None, "b": None}
    count = values.size
    t = np.linspace(0, 2 * (count - 1) * np.pi / count, count)
    a = np.zeros(degree)
    b = np.zeros(degree)
    for j in range(1, degree + 1):
        a[j - 1] = float(values @ np.cos(j * t))
        b[j - 1] = float(values @ np.sin(j * t))
    a = 2 * a / count
    b = 2 * b / count
    a0 = float(np.sum(values) / count)
    if count == 2 * degree:
        a[-1] = a[-1] / 2.0
    return {"a0": a0, "a": a, "b": b}


def trigApprox(t, x, m):
    if not is_r_numeric(t):
        raise PracmaError("is.numeric(t) is not TRUE")
    coefficients = trigPoly(x, m)
    abscissa = np.asarray(t, dtype=float)
    y = np.full(abscissa.shape, coefficients["a0"], dtype=float)
    a = coefficients["a"]
    b = coefficients["b"]
    degree = 0 if a is None else a.size
    for j in range(1, degree + 1):
        y = y + a[j - 1] * np.cos(j * abscissa) + b[j - 1] * np.sin(j * abscissa)
    return y
