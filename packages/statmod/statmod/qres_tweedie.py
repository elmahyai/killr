"""Quantile residuals for Tweedie GLMs.

Translated from statmod 1.5.2 ``qres.tweedie`` in ``R/qres.R``.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import chi2, gamma, norm, poisson

from statmod.digamma import _qnorm
from statmod.pinvgauss import pinvgauss
from statmod.power_fisher_test import _unif


def qres_tweedie(glm_obj, dispersion=None):
    """Quantile residuals for a fitted Tweedie ``glm`` object."""
    mu = np.asarray(glm_obj["fitted_values"], dtype=float).reshape(-1)
    y = np.asarray(glm_obj["y"], dtype=float).reshape(-1)
    df = float(glm_obj["df_residual"])
    prior = glm_obj.get("prior_weights")
    if prior is None:
        w = 1.0
    else:
        w = np.asarray(prior, dtype=float).reshape(-1)
    p = float(glm_obj["var_power"])
    if dispersion is None:
        dispersion = float(np.sum(w * (y - mu) ** 2 / mu**p) / df)
    if isinstance(w, (int, float)) or np.ndim(w) == 0:
        phi = np.full(mu.shape, dispersion / float(w), dtype=np.float64)
    else:
        phi = dispersion / np.asarray(w, dtype=np.float64).reshape(-1)
    u = _ptweedie(y, power=p, mu=mu, phi=phi)
    if 1.0 < p < 2.0:
        zero = y == 0
        if np.any(zero):
            u_zero = u[zero]
            u[zero] = _runif(int(np.sum(zero)), 0.0, u_zero)
    return _qnorm(u)


def _ptweedie(q, *, power: float, mu, phi) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64).reshape(-1)
    mu = np.broadcast_to(np.asarray(mu, dtype=np.float64), q.shape).reshape(-1)
    phi = np.broadcast_to(np.asarray(phi, dtype=np.float64), q.shape).reshape(-1)
    out = np.empty(q.shape, dtype=np.float64)

    if power == 0.0:
        return norm.cdf(q, loc=mu, scale=np.sqrt(phi))
    if power == 1.0:
        return poisson.cdf(q / phi, mu / phi)
    if power == 2.0:
        return gamma.cdf(q, a=1.0 / phi, scale=mu * phi)
    if power == 3.0:
        return np.asarray(
            pinvgauss(q, mean=mu, dispersion=phi, lower_tail=True, log_p=False),
            dtype=np.float64,
        ).reshape(-1)

    out.fill(0.0)
    negative = q < 0
    out[negative] = 0.0
    at_zero = q == 0
    if np.any(at_zero):
        if 0.0 < power < 2.0:
            lam = mu[at_zero] ** (2.0 - power) / (phi[at_zero] * (2.0 - power))
            out[at_zero] = np.exp(-lam)
        else:
            out[at_zero] = 0.0

    positive = q > 0
    if np.any(positive):
        if 1.0 < power < 2.0:
            out[positive] = _ptweedie_series(
                q[positive], power=power, mu=mu[positive], phi=phi[positive]
            )
        elif power > 2.0:
            raise NotImplementedError("ptweedie for power > 2 requires Fourier inversion")
    out = np.clip(out, 0.0, 1.0)
    return out


def _ptweedie_series(q, *, power: float, mu, phi) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64).reshape(-1)
    mu = np.asarray(mu, dtype=np.float64).reshape(-1)
    phi = np.asarray(phi, dtype=np.float64).reshape(-1)
    n = q.size
    cdf = np.zeros(n, dtype=np.float64)

    lam = mu ** (2.0 - power) / (phi * (2.0 - power))
    tau = phi * (power - 1.0) * mu ** (power - 1.0)
    alpha = (2.0 - power) / (1.0 - power)
    drop = 39.0

    lam_max = float(np.max(lam))
    logfmax = -math.log(lam_max) / 2.0
    estlogf = logfmax
    n_index = max(lam_max, 1.0)
    while estlogf > (logfmax - drop) and n_index > 1.0:
        n_index = max(1.0, n_index - 2.0)
        estlogf = (
            -lam_max
            + n_index * (math.log(lam_max) - math.log(n_index) + 1.0)
            - math.log(n_index) / 2.0
        )
    lo_n = max(1, int(math.floor(n_index)))

    lam_min = float(np.min(lam))
    logfmax = -math.log(lam_min) / 2.0
    estlogf = logfmax
    n_index = max(lam_min, 1.0)
    while estlogf > (logfmax - drop):
        n_index += 1.0
        estlogf = (
            -lam_min
            + n_index * (math.log(lam_min) - math.log(n_index) + 1.0)
            - math.log(n_index) / 2.0
        )
    hi_n = max(int(math.ceil(n_index)), lo_n)
    hi_n = min(hi_n, 1_000_000)

    n_vec = np.arange(lo_n, hi_n + 1, dtype=np.float64)
    dfs = -2.0 * alpha * n_vec

    for obs in range(n):
        pois_den = poisson.pmf(n_vec.astype(int), lam[obs])
        arg = 2.0 * q[obs] / tau[obs]
        inc = chi2.cdf(arg, df=dfs)
        cdf[obs] = float(np.dot(inc, pois_den) + math.exp(-lam[obs]))

    return cdf


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
