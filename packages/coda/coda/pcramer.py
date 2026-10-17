"""Cramer-von Mises distribution function.

Translated from coda 0.19-4.1 ``pcramer`` in ``R/heidel.R``.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.special import gamma, kv


def pcramer(q, eps=1.0e-5):
    """Distribution function of the Cramer-von Mises statistic.

    Four series terms. A term is zero when ``(4k+1)^2 / (16q)`` exceeds
    ``-log(eps)``. ``q`` is a vector of quantiles.
    """
    log_eps = math.log(float(eps))
    values = np.asarray(q, dtype=np.float64).reshape(-1)
    total = np.zeros(values.size, dtype=np.float64)
    cutoff = -log_eps
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        for k in range(4):
            coefficient = gamma(k + 0.5) * math.sqrt(4 * k + 1) / (
                gamma(k + 1) * math.pi ** 1.5
            )
            z = coefficient / np.sqrt(values)
            u = (4 * k + 1) ** 2 / (16.0 * values)
            safe_u = np.where(u > 0.0, u, np.nan)
            term = z * np.exp(-u) * kv(0.25, safe_u)
            total = total + np.where(u > cutoff, 0.0, term)
    return total
