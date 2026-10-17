"""Negative binomial random variates from MASS rnegbin."""

from __future__ import annotations

import numpy as np

from extradistr._rgen import rgamma, rpois

from mass.errors import MassError


def rnegbin(n, mu=None, theta=None):
    """Simulate negative binomial counts as Poisson–Gamma mixtures."""
    if theta is None:
        raise MassError("'theta' must be specified")

    n_arr = np.asarray(n, dtype=float).reshape(-1, order="F")
    if n_arr.size > 1:
        k = int(n_arr.size)
        if mu is None:
            mu_arr = n_arr.copy()
        else:
            mu_arr = np.asarray(mu, dtype=float).reshape(-1, order="F")
    else:
        k = int(n_arr[0])
        if mu is None:
            mu_arr = np.full(k, n_arr[0], dtype=float)
        else:
            mu_arr = np.asarray(mu, dtype=float).reshape(-1, order="F")

    theta_arr = np.asarray(theta, dtype=float).reshape(-1, order="F")
    if k == 0:
        return np.array([], dtype=float)

    gammas = np.empty(k, dtype=float)
    for i in range(k):
        th = float(theta_arr[i % theta_arr.size])
        gammas[i] = rgamma(th, scale=1.0)

    out = np.empty(k, dtype=float)
    for i in range(k):
        th = float(theta_arr[i % theta_arr.size])
        m = float(mu_arr[i % mu_arr.size])
        out[i] = rpois((m * gammas[i]) / th)
    return out
