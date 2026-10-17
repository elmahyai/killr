"""Dirichlet random deviates (gtools 3.9.5 ``rdirichlet``)."""

from __future__ import annotations

import numpy as np


def rdirichlet(n, alpha):
    """Generate ``n`` random vectors from the Dirichlet distribution."""
    alpha_vec = np.asarray(alpha, dtype=np.float64).reshape(-1)
    l = int(alpha_vec.size)
    n = int(n)
    if l == 0:
        return np.empty((n, 0), dtype=np.float64)

    from extradistr._rgen import rgamma

    count = l * n
    draws = np.empty(count, dtype=np.float64)
    for i in range(count):
        draws[i] = rgamma(float(alpha_vec[i % l]))
    x = draws.reshape(n, l)
    sm = x.sum(axis=1, keepdims=True)
    return x / sm
