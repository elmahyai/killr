"""Randomized quantile residuals for binomial GLMs.

Translated from statmod 1.5.2 ``qres.binom`` in ``R/qres.R``.
"""

from __future__ import annotations

import math

import numpy as np

from statmod.digamma import _qnorm
from statmod.power_fisher_test import _unif


def qres_binom(glm_obj):
    """Randomized quantile residuals for a fitted binomial ``glm`` object."""
    p = np.asarray(glm_obj["fitted_values"], dtype=float).reshape(-1)
    y = np.asarray(glm_obj["y"], dtype=float).reshape(-1)
    prior = glm_obj.get("prior_weights")
    if prior is None:
        n = np.ones(y.shape, dtype=float)
    else:
        n = np.asarray(prior, dtype=float).reshape(-1)
    y = n * y
    a = _pbinom_vec(y - 1.0, n, p)
    b = _pbinom_vec(y, n, p)
    u = _runif(len(y), a, b)
    return _qnorm(u)


def _pbinom_scalar(q: int, size: int, prob: float) -> float:
    if q < 0:
        return 0.0
    if q >= size:
        return 1.0
    tail = 1.0 - prob
    total = 0.0
    for k in range(q + 1):
        total += math.comb(size, k) * (prob**k) * (tail ** (size - k))
    return total


def _pbinom_vec(q, size, prob) -> np.ndarray:
    q = np.asarray(q, dtype=float).reshape(-1)
    size = np.asarray(size, dtype=float).reshape(-1)
    prob = np.asarray(prob, dtype=float).reshape(-1)
    out = np.empty(prob.shape, dtype=float)
    flat = out.reshape(-1)
    for index in range(flat.size):
        flat[index] = _pbinom_scalar(
            int(math.floor(float(q.reshape(-1)[index]))),
            int(size.reshape(-1)[index]),
            float(prob.reshape(-1)[index]),
        )
    return out


def _runif(n: int, minimum, maximum) -> np.ndarray:
    minimum = np.broadcast_to(np.asarray(minimum, dtype=float), (n,)).reshape(-1)
    maximum = np.broadcast_to(np.asarray(maximum, dtype=float), (n,)).reshape(-1)
    out = np.empty(n, dtype=float)
    for index in range(n):
        lo = float(minimum[index])
        hi = float(maximum[index])
        if hi == lo:
            out[index] = lo
        else:
            out[index] = _unif() * (hi - lo) + lo
    return out
