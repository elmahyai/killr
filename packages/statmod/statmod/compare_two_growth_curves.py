"""Permutation test between two growth-curve groups.

Translated from statmod 1.5.2 ``compareTwoGrowthCurves`` in ``R/growthcurve.R``.
"""

from __future__ import annotations

import numpy as np

from boot.rng import sample_int
from statmod.mean_t import mean_t


def compareTwoGrowthCurves(group, y, nsim=100, fun=None, n0=0.5):
    """Permutation test for two groups of growth curves (rows individuals, columns time)."""
    if fun is None:
        fun = mean_t
    group = np.asarray(group).reshape(-1)
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y.reshape(1, -1)
    g = _unique_in_order(group)
    if len(g) != 2:
        raise ValueError("Must be exactly 2 groups")
    stat_obs = float(fun(y[group == g[0], :], y[group == g[1], :]))
    asbig = 0.0
    n = len(group)
    for _ in range(int(nsim)):
        perm = sample_int(n)
        pgroup = group[np.asarray(perm, dtype=int) - 1]
        stat = float(fun(y[pgroup == g[0], :], y[pgroup == g[1], :]))
        abs_stat = abs(stat)
        abs_obs = abs(stat_obs)
        if abs_stat == abs_obs:
            asbig += 0.5
        if abs_stat > abs_obs:
            asbig += 1.0
    return {"stat": stat_obs, "p.value": (asbig + float(n0)) / (int(nsim) + float(n0))}


def _unique_in_order(values):
    """``unique`` in order of first appearance, like R."""
    seen = set()
    out = []
    for item in values.reshape(-1):
        key = item.item() if isinstance(item, np.generic) else item
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out
