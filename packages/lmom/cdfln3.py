"""Three-parameter lognormal CDF, a port of lmom 3.3 R/lmom.r cdfln3.

para = (xi, mu, sigma): plnorm(x - xi, meanlog = mu, sdlog = sigma).
plnorm is 0 at q <= 0 and pnorm(log(q), mu, sigma) above that.
"""
from __future__ import annotations

import numpy as np
from scipy import special

from ._cdf_common import scalarize


def cdfln3(x, para=(0.0, 0.0, 1.0)):
    p = np.asarray(para, dtype=float).ravel()
    if p.size != 3:
        raise ValueError("parameter vector has wrong length")
    if np.any(np.isnan(p)):
        raise ValueError("missing values in parameter vector")
    xi, mu, sigma = p
    if sigma <= 0:
        raise ValueError("distribution parameters invalid")

    q = np.asarray(x, dtype=float) - xi
    with np.errstate(all="ignore"):
        positive = q > 0
        logq = np.log(np.where(positive, q, 1.0))
        value = np.where(positive, special.ndtr((logq - mu) / sigma), 0.0)
    value = np.where(np.isnan(q), np.nan, value)
    return scalarize(x, value)
