"""Weibull distribution parameters from L-moments."""

from __future__ import annotations

import math

import numpy as np

from .pelgev import pelgev


def pelwei(xmom, bound=None):
    """Return Weibull parameters, optionally with a lower bound."""
    values = np.asarray(xmom, dtype=float).ravel()
    if bound is not None:
        if values.size < 2:
            raise ValueError("with bound specified, need at least 2 L-moments")
        lam1 = values[0] - bound
        if lam1 <= 0 or values[1] <= 0 or values[1] >= lam1:
            raise ValueError("invalid L-moments")
        delta = -math.log(2.0) / math.log1p(-values[1] / lam1)
        beta = lam1 / math.gamma(1.0 + 1.0 / delta)
        return np.array([bound, beta, delta])
    if values.size < 3:
        raise ValueError("need at least 3 L-moments")
    if values[1] <= 0 or values[2] >= 1:
        raise ValueError("invalid L-moments")
    pg = pelgev(np.array([-values[0], values[1], -values[2]]))
    delta = 1.0 / pg[2]
    beta = pg[1] / pg[2]
    return np.array([-pg[0] - beta, beta, delta])
