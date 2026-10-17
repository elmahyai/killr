"""Quantiles of the Anderson-Darling null: goftest 1.2-3 qAD (R/andarl.R).

Each quantile is R's uniroot on pAD - p over c(0, 1) with extendInt = "up".
"""

from __future__ import annotations

import numpy as np

from goftest._common import uniroot_up
from goftest.pAD import pAD


def qAD(p, n=np.inf, lower_tail=True, fast=True):
    p = np.asarray(p, dtype=float).ravel()
    if np.any(p < 0) or np.any(p > 1):
        raise ValueError("p must be in [0, 1]")
    if not lower_tail:
        p = 1.0 - p
    ans = np.full(p.shape, np.nan)
    for i in np.flatnonzero((p >= 0) & (p < 1)):
        ans[i] = uniroot_up(
            lambda x, pi=p[i]: float(pAD(np.array([x]), n, fast=fast)[0]) - pi,
            0.0,
            1.0,
        )
    return ans
