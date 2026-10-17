"""Kaplan--Meier mean residual life."""

from __future__ import annotations

import numpy as np


def km_mrl(times, cens):
    times = np.asarray(times, dtype=float).reshape(-1)
    cens = np.asarray(cens).reshape(-1)
    if times.size != cens.size:
        raise ValueError("times and cens must have equal length")
    n = times.size
    order = np.argsort(times, kind="quicksort")
    ts = times[order]
    cs = cens[order]
    alive = np.arange(n, 0, -1, dtype=float)
    hazard = (1.0 - cs) / alive
    if n == 1:
        result = np.array([0.0])
    else:
        survival = np.exp(np.cumsum(np.log1p(-hazard[:-1])))
        integral = np.diff(ts) * survival
        result = np.r_[np.cumsum(integral[::-1])[::-1] / survival, 0.0]
        result[cs == 0] = 0.0
    out = np.empty(n, dtype=float)
    out[order] = result
    return out


__all__ = ["km_mrl"]
