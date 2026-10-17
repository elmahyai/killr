"""Pearson type III CDF, a port of lmom 3.3 R/lmom.r cdfpe3.

para = (mu, sigma, gamma). Near-zero skew is the normal CDF. Otherwise the
CDF is a gamma CDF with shape alpha = 4 / gamma^2, and a negative skew takes
the complement.
"""
from __future__ import annotations

import numpy as np
from scipy import special

from ._cdf_common import scalarize


def cdfpe3(x, para=(0.0, 1.0, 0.0)):
    p = np.asarray(para, dtype=float).ravel()
    if p.size != 3:
        raise ValueError("parameter vector has wrong length")
    if np.any(np.isnan(p)):
        raise ValueError("missing values in parameter vector")
    mu, sigma, gamma = p
    if sigma <= 0:
        raise ValueError("distribution parameters invalid")

    xs = np.asarray(x, dtype=float)
    with np.errstate(all="ignore"):
        if abs(gamma) <= 1e-6:
            return scalarize(x, special.ndtr((xs - mu) / sigma))
        alpha = 4.0 / gamma ** 2
        z = 2.0 * (xs - mu) / (sigma * gamma) + alpha
        result = special.gammainc(alpha, np.maximum(0.0, z))
        if gamma < 0:
            result = 1.0 - result
    return scalarize(x, result)
