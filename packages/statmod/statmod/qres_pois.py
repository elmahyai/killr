"""Quantile residuals for Poisson GLMs.

Translated from statmod 1.5.2 ``qres.pois`` in ``R/qres.R``.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import poisson

from statmod.digamma import _qnorm
from statmod.power_fisher_test import _unif


def qres_pois(glm_obj):
    """Quantile residuals for a fitted Poisson ``glm`` object."""
    y = np.asarray(glm_obj["y"], dtype=float).reshape(-1)
    mu = np.asarray(glm_obj["fitted_values"], dtype=float).reshape(-1)
    a = poisson.cdf(y - 1.0, mu)
    b = poisson.cdf(y, mu)
    u = _runif(len(y), a, b)
    return _qnorm(u)


def _runif(n: int, minimum, maximum) -> np.ndarray:
    minimum = np.broadcast_to(np.asarray(minimum, dtype=float), (n,)).reshape(-1)
    maximum = np.broadcast_to(np.asarray(maximum, dtype=float), (n,)).reshape(-1)
    out = np.empty(n, dtype=float)
    for index in range(n):
        lo = float(minimum[index])
        hi = float(maximum[index])
        if hi == lo:
            out[index] = lo
        else:
            out[index] = _unif() * (hi - lo) + lo
    return out
