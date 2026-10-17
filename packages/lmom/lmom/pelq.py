from __future__ import annotations

import numpy as np

from .lmrq import lmrq
from .lmrp import lmrp


def _fit(lmom, func, start, kind, use_cdf, **kwargs):
    target = np.asarray(lmom, dtype=float).ravel()
    start = np.asarray(start, dtype=float).ravel()
    if target.size < 2:
        raise ValueError("at least two L-moments are required")
    def objective(p):
        try:
            q = (lambda u: func(u, p)) if not use_cdf else (lambda x: func(x, p))
            got = (lmrq(q, order=target.size, ratios=True, **kwargs)
                   if not use_cdf else lmrp(
                       lambda x: func(x, p), order=target.size, ratios=True, **kwargs))
            return float(np.sum((np.asarray(got) - target) ** 2))
        except Exception:
            return np.inf
    simplex = np.vstack([start, *[start + np.eye(start.size)[i] * (abs(start[i]) * .05 + .05)
                                   for i in range(start.size)]])
    for _ in range(80):
        scores = [objective(p) for p in simplex]
        order = np.argsort(scores)
        simplex = simplex[order]
        if np.max(np.abs(simplex[1:] - simplex[0])) < 1e-8:
            break
        centroid = simplex[:-1].mean(axis=0)
        reflected = centroid + (centroid - simplex[-1])
        if objective(reflected) < scores[order[-2]]:
            simplex[-1] = reflected
        else:
            simplex[1:] = simplex[0] + .5 * (simplex[1:] - simplex[0])
    return simplex[0]


def pelq(lmom, qfunc, start, type="n", **kwargs):
    """Estimate parameters by matching L-moments of a quantile function."""
    return _fit(lmom, qfunc, start, type, False, **kwargs)
