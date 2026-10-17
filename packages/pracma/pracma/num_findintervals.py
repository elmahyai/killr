"""Indices of intervals that contain a scalar."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, is_r_vector, r_length


def findintervals(x, xs):
    if r_length(x) == 0 or r_length(xs) == 0:
        return None
    if not (is_r_vector(x) and is_r_numeric(x)):
        raise PracmaError("Arguments 'x' and 'xs' must be numeric vectors.")
    if r_length(x) != 1:
        raise PracmaError("Length of vector 'x' must be 1.")
    target = float(np.asarray(x, dtype=float).reshape(-1)[0])
    grid = np.asarray(xs, dtype=float).reshape(-1)
    delta = grid - target
    exact = np.flatnonzero(delta == 0) + 1
    products = delta[:-1] * delta[1:]
    crossing = np.flatnonzero(products < 0) + 1
    return np.sort(np.concatenate([exact, crossing])).astype(float)
