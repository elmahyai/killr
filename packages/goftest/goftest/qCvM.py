"""Quantiles of the Cramer-von Mises null: goftest 1.2-3 qCvM (R/cramer.R).

Each quantile is R's uniroot on pCvM - p over c(lower, 1) with extendInt = "up".
"""

from __future__ import annotations

import math

import numpy as np

from goftest._common import uniroot_up
from goftest.pCvM import pCvM


def qCvM(p, n=np.inf, lower_tail=True):
    p = np.asarray(p, dtype=float).ravel()
    if np.any(p < 0) or np.any(p > 1):
        raise ValueError("p must be in [0, 1]")
    if not lower_tail:
        p = 1.0 - p
    finite = math.isfinite(n)
    lower = 1.0 / (12.0 * n) if finite else 0.0
    upper = n / 3.0 if finite else math.inf
    ans = np.zeros(p.shape)
    small = p <= 2e-10
    large = (1.0 - p) <= 2e-10
    ans[small] = lower
    ans[large] = upper
    for i in np.flatnonzero(~small & ~large):
        ans[i] = uniroot_up(
            lambda x, pi=p[i]: float(pCvM(np.array([x]), n)[0]) - pi,
            lower,
            1.0,
        )
    return ans
