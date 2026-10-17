"""Lebesgue constant of a 1-d node set."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric

_EPS = float(np.finfo(float).eps)


def lebesgue(x, refine=4, plotting=False):
    if not is_r_numeric(x):
        raise PracmaError("Argument 'x' must be a numeric vector.")
    if int(refine) not in (2, 3, 4, 5, 6, 7, 8, 9, 10) or float(refine) != int(refine):
        raise PracmaError("Argument 'refine' must be one of 2,3,4,5,6,7,8,9,10.")
    nodes = np.asarray(x, dtype=float).reshape(-1)
    count = nodes.size
    grid_count = 2 ** int(refine) * count + 1
    repeated = np.tile(nodes.reshape(-1, 1), (1, count))
    weights = 1.0 / np.prod(repeated - repeated.T + np.eye(count), axis=1)
    grid = np.linspace(np.min(nodes), np.max(nodes), grid_count)
    difference = np.repeat(grid.reshape(1, -1), count, axis=0) - np.repeat(nodes.reshape(-1, 1), grid_count, axis=1)
    singular = difference == 0
    product = np.prod(difference, axis=0)
    difference = difference.copy()
    difference[singular] = _EPS
    scaled = (np.diag(weights) @ np.tile(product, (count, 1))) / difference
    return float(np.max(np.sum(np.abs(scaled), axis=0)))
