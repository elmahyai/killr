"""Quantile residuals for negative binomial GLMs.

Translated from statmod 1.5.2 ``qres.nbinom`` in ``R/qres.R``.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import beta

from statmod.digamma import _qnorm
from statmod.power_fisher_test import _unif


def qres_nbinom(glm_obj):
    """Quantile residuals for a fitted negative binomial ``glm`` object."""
    y = np.asarray(glm_obj["y"], dtype=float).reshape(-1)
    theta = glm_obj.get("theta")
    if theta is None:
        size = float(glm_obj["family_size"])
    else:
        size = float(theta)
    mu = np.asarray(glm_obj["fitted_values"], dtype=float).reshape(-1)
    p = size / (mu + size)
    y_pos = y > 0
    a = np.zeros(y.shape, dtype=float)
    if np.any(y_pos):
        a[y_pos] = beta.cdf(p[y_pos], size, np.maximum(y[y_pos], 1.0))
    b = beta.cdf(p, size, y + 1.0)
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
