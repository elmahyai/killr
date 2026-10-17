"""Inverse Gaussian cumulative distribution.

Translated from statmod 1.5.2 ``pinvgauss`` in ``R/invgauss.R``.
"""

from __future__ import annotations

import math

import numpy as np

_LOG2PI = math.log(2.0 * math.pi)
_LOG_PI = math.log(math.pi)


def _rep_len(values, length: int) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    flat = arr.reshape(-1)
    if flat.size == 0:
        return np.array([], dtype=np.float64)
    if flat.size == 1:
        return np.full(length, float(flat[0]), dtype=np.float64)
    if flat.size < length:
        reps = int(math.ceil(length / flat.size))
        flat = np.tile(flat, reps)[:length]
    elif flat.size > length:
        flat = flat[:length]
    return np.asarray(flat, dtype=np.float64)


def _pnorm_log(x: np.ndarray, *, lower_tail: bool) -> np.ndarray:
    from scipy.special import log_ndtr

    z = np.asarray(x, dtype=np.float64)
    if lower_tail:
        return np.asarray(log_ndtr(z), dtype=np.float64)
    return np.asarray(log_ndtr(-z), dtype=np.float64)


def _pchisq_log(q: np.ndarray, df: float, *, lower_tail: bool) -> np.ndarray:
    from scipy.stats import chi2

    q = np.asarray(q, dtype=np.float64)
    if lower_tail:
        return np.asarray(chi2.logcdf(q, df), dtype=np.float64)
    return np.asarray(chi2.logsf(q, df), dtype=np.float64)


def _pgamma_log(
    q: np.ndarray, shape: np.ndarray, scale: np.ndarray, *, lower_tail: bool
) -> np.ndarray:
    from scipy.stats import gamma

    q = np.asarray(q, dtype=np.float64)
    shape = np.asarray(shape, dtype=np.float64)
    scale = np.asarray(scale, dtype=np.float64)
    if lower_tail:
        return np.asarray(gamma.logcdf(q, a=shape, scale=scale), dtype=np.float64)
    return np.asarray(gamma.logsf(q, a=shape, scale=scale), dtype=np.float64)


def _pinvgauss_core(
    q: np.ndarray,
    dispersion: np.ndarray,
    mean: np.ndarray,
    *,
    lower_tail: bool,
) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64)
    dispersion = np.asarray(dispersion, dtype=np.float64)
    mean = np.asarray(mean, dtype=np.float64)
    scaled_q = q / mean
    scaled_phi = dispersion * mean
    pq = np.sqrt(scaled_phi * scaled_q)
    a = _pnorm_log((scaled_q - 1.0) / pq, lower_tail=lower_tail)
    b = 2.0 / scaled_phi + _pnorm_log(-(scaled_q + 1.0) / pq, lower_tail=True)
    if lower_tail:
        b = np.exp(b - a)
    else:
        b = -np.exp(b - a)
    logp = a + np.log1p(b)

    if not lower_tail:
        asymptotic = (scaled_q > 1.0e6) & (scaled_q / 2.0 / scaled_phi > 5.0e5)
        if np.any(asymptotic):
            q_a = scaled_q[asymptotic]
            phi_a = scaled_phi[asymptotic]
            logp[asymptotic] = (
                1.0 / phi_a
                - 0.5 * _LOG_PI
                - np.log(2.0 * phi_a)
                - 1.5 * np.log1p(q_a / 2.0 / phi_a)
                - q_a / 2.0 / phi_a
            )

    return logp


def pinvgauss(
    q,
    mean=1,
    shape=None,
    dispersion=1,
    lower_tail=True,
    log_p=False,
):
    """CDF of the inverse Gaussian distribution."""
    if shape is not None:
        dispersion = 1.0 / np.asarray(shape, dtype=np.float64)

    q_arr = np.asarray(q, dtype=np.float64)
    mean_arr = np.asarray(mean, dtype=np.float64)
    disp_arr = np.asarray(dispersion, dtype=np.float64)

    q_len = 1 if q_arr.size == 0 else q_arr.size
    mean_len = 1 if mean_arr.size == 0 else mean_arr.size
    disp_len = 1 if disp_arr.size == 0 else disp_arr.size
    lengths = (q_len, mean_len, disp_len)
    min_len = min(lengths)
    max_len = max(lengths)

    if min_len == 0:
        return np.array([], dtype=np.float64)

    n = max_len
    q_flat = _rep_len(q_arr, n)
    mu = _rep_len(mean_arr, n)
    phi = _rep_len(disp_arr, n)

    preserve_shape = q_len == n and q_arr.ndim > 1
    out_shape = q_arr.shape if preserve_shape else (n,)

    spec_q = np.any(~np.isfinite(q_flat) | (q_flat <= 0))
    spec_mean = np.any(~np.isfinite(mu) | (mu <= 0))
    spec_disp = np.any(~np.isfinite(phi) | (phi <= 0))
    spec_cv = np.any(mu * phi < 1.0e-14)
    any_special = spec_q or spec_mean or spec_disp or spec_cv

    if any_special:
        logp = q_flat.copy()
        spec_q_mask = np.isnan(q_flat) | (q_flat < 0) | np.isinf(q_flat)
        mu = mu.copy()
        phi = phi.copy()
        mu[spec_q_mask] = 1.0
        phi[spec_q_mask] = 1.0
        mu[phi == np.inf] = 1.0
        phi[mu == 0.0] = 1.0

        left_limit = (
            (q_flat < 0)
            | ((q_flat == 0) & (mu > 0) & (phi < np.inf))
            | ((q_flat < mu) & (phi == 0))
        )
        right_limit = (
            ((q_flat > mu) & ((mu == 0) | (phi == 0)))
            | np.isinf(q_flat)
            | ((q_flat > 0) & (phi == np.inf))
        )
        spike = ((q_flat == mu) & ((mu == 0) | (phi == 0))) | (
            (q_flat == 0) & (phi == np.inf)
        )
        invchisq = (mu == np.inf) & ~(left_limit | right_limit | spike)
        cv2 = mu * phi
        smallcv = (cv2 < 1.0e-14) & ~(left_limit | right_limit | spike)
        na_cases = (
            np.isnan(q_flat)
            | np.isnan(mu)
            | np.isnan(phi)
            | (mu < 0)
            | (phi < 0)
        )
        left_limit = left_limit & ~na_cases
        right_limit = right_limit & ~na_cases
        spike = spike & ~na_cases
        invchisq = invchisq & ~na_cases
        smallcv = smallcv & ~na_cases

        if lower_tail:
            logp[left_limit] = -np.inf
            logp[right_limit] = 0.0
        else:
            logp[left_limit] = 0.0
            logp[right_limit] = -np.inf
        logp[spike] = 0.0

        if np.any(invchisq):
            logp[invchisq] = _pchisq_log(
                1.0 / q_flat[invchisq] / phi[invchisq],
                1.0,
                lower_tail=not lower_tail,
            )
        if np.any(smallcv):
            cv_ok = cv2[smallcv]
            logp[smallcv] = _pgamma_log(
                q_flat[smallcv],
                1.0 / cv_ok,
                cv_ok * mu[smallcv],
                lower_tail=lower_tail,
            )
        logp[na_cases] = np.nan

        ok = ~(left_limit | right_limit | spike | invchisq | smallcv | na_cases)
        if np.any(ok):
            logp[ok] = _pinvgauss_core(
                q_flat[ok],
                phi[ok],
                mu[ok],
                lower_tail=lower_tail,
            )
    else:
        logp = _pinvgauss_core(q_flat, phi, mu, lower_tail=lower_tail)

    if log_p:
        out = logp
    else:
        out = np.exp(logp)

    if preserve_shape:
        return out.reshape(out_shape)
    if out_shape == (n,) and np.asarray(q).ndim == 0 and n == 1:
        return np.float64(out[0])
    return out.reshape(out_shape)
