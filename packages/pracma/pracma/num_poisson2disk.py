"""Poisson-disk-like sampling by farthest candidate."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import distmat


def poisson2disk(n, a=1, b=1, m=10, info=True):
    if a <= 0 or b <= 0:
        raise PracmaError("Width a and height b must be positive reals.")
    if float(n) != math.floor(float(n)) or n < 1 or float(m) != math.floor(float(m)) or m < 1:
        raise PracmaError("n and m must be integer numbers.")
    count = int(n)
    copies = int(m)
    scale = np.repeat([a, b], [copies, copies])
    points = np.zeros((count, 2))
    points[0] = np.array([a, b]) * np.random.random(2)
    for index in range(1, count):
        draws = scale * np.random.random(2 * copies)
        candidates = draws.reshape((copies, 2), order="F")
        distances = distmat(candidates, points[:index])
        chosen = int(np.argmax(np.min(distances, axis=1)))
        points[index] = candidates[chosen]
    if info:
        pairwise = distmat(points, points)
        np.fill_diagonal(pairwise, np.max(pairwise))
        print(f"Minimal Distance between points:  {float(np.min(pairwise))}")
    return points
