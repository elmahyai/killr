"""Canonical parameter for the Digamma GLM family.

Translated from statmod 1.5.2 ``canonic.digamma`` and the helpers it calls in
``R/digammaf.R`` and ``R/digamma.R``.
"""

from __future__ import annotations

import numpy as np

from statmod.d2cumulant_digamma import d2cumulant_digamma


def canonic_digamma(mu):
    """Inverse of ``meanval.digamma``: canonical parameter from the mean ``mu``."""
    mu = np.asarray(mu, dtype=float)
    mlmt = np.log(mu)
    theta = -np.exp(-mlmt)
    for _ in range(3):
        mu1 = _meanval_digamma(theta)
        variance = d2cumulant_digamma(theta)
        deriv = -variance / mu1 * theta
        mlmt = mlmt - np.log(mu1 / mu) / deriv
        theta = -np.exp(-mlmt)
    return np.asarray(theta, dtype=float)


def _meanval_digamma(theta):
    return 2.0 * _logmdigamma(-theta)


def _logmdigamma(z):
    """``log(x) - digamma(x)`` for positive real ``x``."""
    z = np.asarray(z, dtype=float)
    if z.size == 0:
        return z.copy()
    omit = np.isnan(z) | (z <= 0)
    if np.any(omit):
        out = np.full(z.shape, np.nan, dtype=float)
        good = ~omit
        out[good] = _logmdigamma(z[good])
        return out
    if np.any(z < 5):
        out = np.empty_like(z)
        small = z < 5
        x = z[small]
        out[small] = (
            np.log(x / (x + 5))
            + _logmdigamma(x + 5)
            + 1.0 / x
            + 1.0 / (x + 1)
            + 1.0 / (x + 2)
            + 1.0 / (x + 3)
            + 1.0 / (x + 4)
        )
        if np.any(~small):
            out[~small] = _logmdigamma(z[~small])
        return out
    return _logmdigamma_asymptotic(z)


def _logmdigamma_asymptotic(z):
    z = np.asarray(z, dtype=float)
    x = 1.0 / z**2
    tail = x * (
        -1.0 / 12.0
        + (
            x
            * (
                1.0 / 120.0
                + (
                    x
                    * (
                        -1.0 / 252.0
                        + (
                            x
                            * (
                                1.0 / 240.0
                                + (
                                    x
                                    * (
                                        -1.0 / 132.0
                                        + (
                                            x
                                            * (
                                                691.0 / 32760.0
                                                + (x * (-1.0 / 12.0 + (3617.0 * x) / 8160.0))
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )
    return 1.0 / (2.0 * z) - tail
