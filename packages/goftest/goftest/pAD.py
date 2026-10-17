"""Null distribution of the Anderson-Darling statistic: goftest 1.2-3 pAD (R/andarl.R).

The three kernels are goftest_kernels (crates/goftest), the Rust port of
src/AnDarl.c and src/ADinf.c.
"""

from __future__ import annotations

import numpy as np

import goftest_kernels as gk


def pAD(q, n=np.inf, lower_tail=True, fast=True):
    """cdf of the A_n statistic at q. n = Inf gives the limiting law."""
    q = np.asarray(q, dtype=float).ravel()
    p = np.full(q.shape, np.nan)
    p[np.isposinf(q)] = 1.0
    p[(np.isfinite(q) & (q <= 0)) | np.isneginf(q)] = 0.0
    ok = np.isfinite(q) & (q > 0)
    if ok.any():
        arg = np.ascontiguousarray(q[ok])
        if np.isfinite(n):
            p[ok] = gk.ad_prob_n(arg, int(n))
        elif fast:
            p[ok] = gk.adinf(arg)
        else:
            p[ok] = gk.ad_inf(arg)
    if not lower_tail:
        p = 1.0 - p
    return p
