"""Random Gumbel draws (ordinal rgumbel)."""

from __future__ import annotations

import math

import numpy as np

from boot.rng import unif


def rgumbel(n, location=0.0, scale=1.0, max=True):
    """Sample from the Gumbel max or min distribution."""
    count = int(n)
    out = np.empty(count, dtype=np.float64)
    sign = -1.0 if max else 1.0
    loc = float(location)
    sc = float(scale)
    for i in range(count):
        out[i] = loc + sign * sc * math.log(-math.log(unif()))
    return out
