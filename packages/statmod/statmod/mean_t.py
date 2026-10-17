"""Mean t-statistic between two growth-curve groups.

Translated from statmod 1.5.2 ``meanT`` in ``R/growthcurve.R``.
"""

from __future__ import annotations

import numpy as np


def mean_t(y1, y2):
    """Pooled two-sample t-statistics over time, weighted by degrees of freedom."""
    y1 = np.asarray(y1, dtype=float)
    y2 = np.asarray(y2, dtype=float)
    if y1.ndim < 2 or y2.ndim < 2:
        return float(np.nan)
    if y1.shape[1] != y2.shape[1]:
        raise ValueError("Number of time points must match")
    m1 = np.nanmean(y1, axis=0)
    m2 = np.nanmean(y2, axis=0)
    v1 = np.nanvar(y1, axis=0, ddof=1)
    v2 = np.nanvar(y2, axis=0, ddof=1)
    n1 = np.sum(~np.isnan(y1), axis=0).astype(float)
    n2 = np.sum(~np.isnan(y2), axis=0).astype(float)
    pooled = n1 + n2 - 2
    s = ((n1 - 1) * v1 + (n2 - 1) * v2) / pooled
    t_stat = (m1 - m2) / np.sqrt(s * (1 / n1 + 1 / n2))
    weights = pooled / (n1 + n2)
    keep = ~np.isnan(t_stat)
    if not np.any(keep):
        return float(np.nan)
    x = t_stat[keep]
    w = weights[keep]
    return float(np.sum(x * w) / np.sum(w))
