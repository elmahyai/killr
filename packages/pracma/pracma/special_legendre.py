"""Associated Legendre functions."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_numeric_value, length_of, stop_unless
from pracma.special_poly import polyder, polyval


def legendre(n, x):
    stop_unless(is_numeric_value(x), "is.numeric(x) is not TRUE")
    stop_unless(is_numeric_value(n), "is.numeric(n) is not TRUE")
    stop_unless(length_of(n) == 1, "length(n) == 1 is not TRUE")
    degree = float(np.asarray(n).reshape(-1)[0])
    stop_unless(math.floor(degree) == math.ceil(degree), "floor(n) == ceiling(n) is not TRUE")
    stop_unless(degree >= 0, "n >= 0 is not TRUE")
    degree = int(degree)
    points = np.ravel(np.asarray(x, dtype=float), order="F")
    width = points.size
    if degree == 0:
        return np.ones(width)
    table = np.zeros((degree + 1, degree + 1))
    table[0, degree] = 1.0
    table[1, degree - 1] = 1.0
    if degree > 1:
        for i_r in range(3, degree + 2):
            j = i_r - 1
            row = i_r - 1
            col_start = degree - i_r + 1
            prev_start = degree - i_r + 2
            left = np.concatenate([table[row - 1, prev_start : degree + 1], [0.0]])
            right = table[row - 2, col_start : degree + 1]
            table[row, col_start : degree + 1] = (2 * j - 1) / j * left - (j - 1) / j * right
    coeffs = table[degree, :]
    values = np.empty((degree + 1, width))
    values[0, :] = np.asarray(polyval(coeffs, points), dtype=float).reshape(-1)
    for j in range(1, degree + 1):
        coeffs = polyder(coeffs)
        values[j, :] = ((-1) ** j) * np.sqrt((1.0 - points**2) ** j) * np.asarray(
            polyval(coeffs, points), dtype=float
        ).reshape(-1)
    return values
