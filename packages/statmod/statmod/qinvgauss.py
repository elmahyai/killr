"""Inverse Gaussian quantile function.

Translated from statmod 1.5.2 ``qinvgauss`` in ``R/invgauss.R``.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from statmod.dinvgauss import _dinvgauss_core
from statmod.pinvgauss import _pinvgauss_core


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


def _qnorm_logp(
    logp: np.ndarray, *, lower_tail: bool
) -> np.ndarray:
    from scipy.stats import norm

    logp = np.asarray(logp, dtype=np.float64)
    p = np.exp(logp)
    if lower_tail:
        return np.asarray(norm.ppf(p), dtype=np.float64)
    return np.asarray(norm.isf(p), dtype=np.float64)


def _qchisq_logp(
    logp: np.ndarray, df: float, *, lower_tail: bool
) -> np.ndarray:
    from scipy.stats import chi2

    logp = np.asarray(logp, dtype=np.float64)
    p = np.exp(logp)
    if lower_tail:
        return np.asarray(chi2.ppf(p, df), dtype=np.float64)
    return np.asarray(chi2.isf(p, df), dtype=np.float64)


def _qgamma_logp_shape_rate(
    logp: np.ndarray, shape: np.ndarray, rate: np.ndarray, *, lower_tail: bool
) -> np.ndarray:
    from scipy.stats import gamma

    logp = np.asarray(logp, dtype=np.float64)
    shape = np.asarray(shape, dtype=np.float64)
    rate = np.asarray(rate, dtype=np.float64)
    p = np.exp(logp)
    scale = 1.0 / rate
    if lower_tail:
        return np.asarray(gamma.ppf(p, a=shape, scale=scale), dtype=np.float64)
    return np.asarray(gamma.isf(p, a=shape, scale=scale), dtype=np.float64)


def _qgamma_logp_shape_scale(
    logp: np.ndarray, shape: np.ndarray, scale: np.ndarray, *, lower_tail: bool
) -> np.ndarray:
    from scipy.stats import gamma

    logp = np.asarray(logp, dtype=np.float64)
    shape = np.asarray(shape, dtype=np.float64)
    scale = np.asarray(scale, dtype=np.float64)
    p = np.exp(logp)
    if lower_tail:
        return np.asarray(gamma.ppf(p, a=shape, scale=scale), dtype=np.float64)
    return np.asarray(gamma.isf(p, a=shape, scale=scale), dtype=np.float64)


def _newton_step(
    x: np.ndarray,
    p: np.ndarray,
    logp: np.ndarray,
    phi: np.ndarray,
    *,
    lower_tail: bool,
) -> np.ndarray:
    unit = np.ones_like(phi)
    log_f = _pinvgauss_core(x, phi, unit, lower_tail=lower_tail)
    dlogp = logp - log_f
    smallstep = np.abs(dlogp) < 1.0e-5
    dp = np.empty_like(p)
    dp[smallstep] = (
        np.exp(logp[smallstep] + np.log1p(-dlogp[smallstep] / 2.0)) * dlogp[smallstep]
    )
    dp[~smallstep] = p[~smallstep] - np.exp(log_f[~smallstep])
    dens = _dinvgauss_core(x, phi, unit, log=False)
    return dp / dens


def qinvgauss(
    p,
    mean=1,
    shape=None,
    dispersion=1,
    lower_tail=True,
    log_p=False,
    maxit=200,
    tol=1.0e-14,
    trace=False,
):
    """Quantiles of the inverse Gaussian distribution."""
    if shape is not None:
        dispersion = 1.0 / np.asarray(shape, dtype=np.float64)

    p_arr = np.asarray(p, dtype=np.float64)
    mean_arr = np.asarray(mean, dtype=np.float64)
    disp_arr = np.asarray(dispersion, dtype=np.float64)

    if log_p:
        logp = p_arr.reshape(-1).copy()
        prob = np.exp(logp)
    else:
        prob = p_arr.reshape(-1).copy()
        prob[prob < 0] = np.nan
        prob[prob > 1] = np.nan
        with np.errstate(divide="ignore", invalid="ignore"):
            logp = np.log(prob)

    p_len = 1 if prob.size == 0 else prob.size
    mean_len = 1 if mean_arr.size == 0 else mean_arr.size
    disp_len = 1 if disp_arr.size == 0 else disp_arr.size
    lengths = (p_len, mean_len, disp_len)
    min_len = min(lengths)
    max_len = max(lengths)

    if min_len == 0:
        return np.array([], dtype=np.float64)

    n = max_len
    preserve_shape = p_len == n and p_arr.ndim > 1
    out_shape = p_arr.shape if preserve_shape else (n,)

    if prob.size < n:
        logp = _rep_len(logp, n)
        prob = _rep_len(prob, n)
    elif prob.size > n:
        logp = logp[:n]
        prob = prob[:n]

    mu = _rep_len(mean_arr, n)
    phi = _rep_len(disp_arr, n)

    q = prob.copy()

    na_cases = np.isnan(prob) | np.isnan(mu) | np.isnan(phi) | (mu <= 0) | (phi <= 0)
    if lower_tail:
        left_limit = logp == -np.inf
        right_limit = logp == 0.0
    else:
        left_limit = logp == 0.0
        right_limit = logp == -np.inf

    q[left_limit] = 0.0
    q[right_limit] = np.inf
    q[na_cases] = np.nan

    ok = ~(na_cases | left_limit | right_limit)

    invchisq = (mu == np.inf) & ok
    if np.any(invchisq):
        q[invchisq] = (
            1.0
            / _qchisq_logp(logp[invchisq], 1.0, lower_tail=not lower_tail)
            / phi[invchisq]
        )
        ok[invchisq] = False

    cv2 = phi * mu
    smallcv = (cv2 < 1.0e-8) & ok
    if np.any(smallcv):
        cv_ok = cv2[smallcv]
        q[smallcv] = _qgamma_logp_shape_scale(
            logp[smallcv],
            1.0 / cv_ok,
            cv_ok * mu[smallcv],
            lower_tail=lower_tail,
        )
        ok[smallcv] = False

    if not np.any(ok):
        return _finalize_q(q, preserve_shape, out_shape, p_arr, n)

    phi_ok = cv2[ok]
    logp_ok = logp[ok]
    p_ok = prob[ok]
    mu_ok = mu[ok]

    kappa = 1.5 * phi_ok
    x = np.sqrt(1.0 + kappa**2) - kappa
    bigcv = kappa > 1.0e3
    if np.any(bigcv):
        k1 = 1.0 / 2.0 / kappa[bigcv]
        x[bigcv] = k1 * (1.0 - k1**2)

    if trace:
        if n < 6:
            print("mode ", x)
        else:
            print("quantile(mode) ", np.quantile(x, [0.0, 0.25, 0.5, 0.75, 1.0]))

    if lower_tail:
        small_left = logp_ok < -11.51
        small_right = logp_ok > -1.0e-5
    else:
        small_left = logp_ok > -1.0e-5
        small_right = logp_ok < -11.51

    if np.any(small_left):
        z = _qnorm_logp(logp_ok[small_left], lower_tail=lower_tail)
        x[small_left] = 1.0 / phi_ok[small_left] / z**2

    if np.any(small_right):
        alpha = 1.0 / phi_ok[small_right]
        q_gam = _qgamma_logp_shape_rate(
            logp_ok[small_right],
            alpha,
            alpha,
            lower_tail=lower_tail,
        )
        x[small_right] = np.maximum(x[small_right], q_gam)

    iter_count = 0
    dx = _newton_step(x, p_ok, logp_ok, phi_ok, lower_tail=lower_tail)
    dx[np.isnan(dx)] = 0.0
    sdx = np.sign(dx)
    if lower_tail:
        x = x + dx
    else:
        x = x - dx
    converging = np.abs(dx) > tol

    if trace:
        print(f"Iter= {iter_count} Still converging= {np.sum(converging)}")
        if n < 6:
            print("x ", x, "\ndx ", dx)
        else:
            print(
                "quantile(x) ",
                np.quantile(x, [0.0, 0.25, 0.5, 0.75, 1.0]),
                "\nMax dx ",
                np.max(np.abs(dx)),
            )

    while np.any(converging):
        iter_count += 1
        if iter_count > maxit:
            warnings.warn("max iterations exceeded", RuntimeWarning, stacklevel=2)
            break
        idx = converging
        dx = _newton_step(
            x[idx], p_ok[idx], logp_ok[idx], phi_ok[idx], lower_tail=lower_tail
        )
        bad = np.isnan(dx) | (dx * sdx[idx] < 0)
        dx[bad] = 0.0
        if lower_tail:
            x[idx] = x[idx] + dx
        else:
            x[idx] = x[idx] - dx
        sdx[idx] = np.where(bad, sdx[idx], np.sign(dx))
        converging[idx] = np.abs(dx) / np.maximum(x[idx], 1.0) > tol

        if trace:
            print(f"Iter= {iter_count} Still converging= {np.sum(converging)}")
            if n < 6:
                print("x ", x, "\ndx ", dx)
            else:
                print(
                    "quantile(x) ",
                    np.quantile(x, [0.0, 0.25, 0.5, 0.75, 1.0]),
                    "\nMax dx ",
                    np.max(np.abs(dx)),
                )

    q[np.flatnonzero(ok)] = x * mu_ok
    return _finalize_q(q, preserve_shape, out_shape, p_arr, n)


def _finalize_q(q, preserve_shape, out_shape, p_arr, n):
    if preserve_shape:
        return q.reshape(out_shape)
    if out_shape == (n,) and np.asarray(p_arr).ndim == 0 and n == 1:
        return np.float64(q[0])
    return q.reshape(out_shape)
