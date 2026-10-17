"""Polynomial evaluation and derivatives used by the special functions.

Coefficients are highest power first, as in pracma's polyval.
"""

from __future__ import annotations

import numpy as np


def polyval(p, x):
    coeffs = np.asarray(p).reshape(-1)
    base = np.asarray(x)
    if base.size == 0:
        return np.array([], dtype=float)
    if coeffs.size == 0:
        return np.zeros(np.shape(base), dtype=float)
    dtype = np.result_type(coeffs, base, np.float64)
    acc = np.zeros(np.shape(base), dtype=dtype)
    degree = coeffs.size - 1
    for index, coef in enumerate(coeffs):
        acc = acc + coef * base ** (degree - index)
    return acc


def polyder(p):
    coeffs = np.asarray(p).reshape(-1)
    count = coeffs.size
    if count <= 1:
        return np.zeros(1, dtype=np.result_type(coeffs, np.float64))
    derived = np.arange(count - 1, 0, -1, dtype=float) * coeffs[: count - 1]
    while derived.size >= 2 and derived[0] == 0:
        derived = derived[1:]
    return derived
