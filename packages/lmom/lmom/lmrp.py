from __future__ import annotations

import numpy as np

from .lmrq import lmrq


def lmrp(pfunc, bounds=(-np.inf, np.inf), symm=False, order=1, ratios=True,
         trim=0, acc=1e-6, subdiv=100, verbose=False, **kwargs):
    """Population L-moments computed from a cumulative distribution function."""
    if not callable(pfunc):
        raise TypeError("pfunc must be callable")
    lo, hi = bounds

    def quantile(prob):
        prob = np.asarray(prob, dtype=float)
        if np.isfinite(lo) and np.isfinite(hi):
            grid = np.linspace(float(lo), float(hi), 2001)
            vals = np.asarray(pfunc(grid), dtype=float)
            if vals.shape == grid.shape and np.all(np.diff(vals) >= 0):
                return np.interp(prob, vals, grid)
        out = np.empty_like(prob)
        for i, target in np.ndenumerate(prob):
            a = -10.0 if not np.isfinite(lo) else float(lo)
            b = 10.0 if not np.isfinite(hi) else float(hi)
            for _ in range(80):
                pa = float(np.asarray(pfunc(a)))
                pb = float(np.asarray(pfunc(b)))
                if pa <= target <= pb:
                    break
                if pa > target:
                    a *= 2.0
                if pb < target:
                    b *= 2.0
            for _ in range(70):
                m = (a + b) / 2.0
                if float(np.asarray(pfunc(m))) < target:
                    a = m
                else:
                    b = m
            out[i] = (a + b) / 2.0
        return out

    return lmrq(quantile, bounds=(0, 1), symm=symm, order=order,
                ratios=ratios, trim=trim, acc=acc, subdiv=subdiv,
                verbose=verbose, **kwargs)
