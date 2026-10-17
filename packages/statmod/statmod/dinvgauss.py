"""Inverse Gaussian density.

Translated from statmod 1.5.2 ``dinvgauss`` in ``R/invgauss.R``.
"""

from __future__ import annotations

import math

import numpy as np

_LOG2PI = math.log(2.0 * math.pi)


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


def _dinvgauss_core(x, dispersion, mean, log: bool) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    dispersion = np.asarray(dispersion, dtype=np.float64)
    mean = np.asarray(mean, dtype=np.float64)
    scaled_x = x / mean
    scaled_phi = dispersion * mean
    d = (
        -np.log(scaled_phi)
        - _LOG2PI
        - 3.0 * np.log(scaled_x)
        - (scaled_x - 1.0) ** 2 / scaled_phi / scaled_x
    ) / 2.0
    d = d - np.log(mean)
    if log:
        return d
    return np.exp(d)


def _dinvgauss_inf_mean(x, dispersion) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    dispersion = np.asarray(dispersion, dtype=np.float64)
    return (-np.log(dispersion) - _LOG2PI - 3.0 * np.log(x) - 1.0 / dispersion / x) / 2.0


def dinvgauss(x, mean=1, shape=None, dispersion=1, log=False):
    """Density of the inverse Gaussian distribution."""
    if shape is not None:
        dispersion = 1.0 / np.asarray(shape, dtype=np.float64)

    x_arr = np.asarray(x, dtype=np.float64)
    mean_arr = np.asarray(mean, dtype=np.float64)
    disp_arr = np.asarray(dispersion, dtype=np.float64)

    x_len = 1 if x_arr.size == 0 else x_arr.size
    mean_len = 1 if mean_arr.size == 0 else mean_arr.size
    disp_len = 1 if disp_arr.size == 0 else disp_arr.size
    lengths = (x_len, mean_len, disp_len)
    min_len = min(lengths)
    max_len = max(lengths)

    if min_len == 0:
        return np.array([], dtype=np.float64)

    n = max_len
    x_flat = _rep_len(x_arr, n)
    mu = _rep_len(mean_arr, n)
    phi = _rep_len(disp_arr, n)

    preserve_shape = x_len == n and x_arr.ndim > 1
    out_shape = x_arr.shape if preserve_shape else (n,)

    logd = x_flat.copy()

    spec_x = np.any(~np.isfinite(x_flat) | (x_flat <= 0))
    spec_mean = np.any(~np.isfinite(mu) | (mu <= 0))
    spec_disp = np.any(~np.isfinite(phi) | (phi <= 0))
    any_special = spec_x or spec_mean or spec_disp

    if any_special:
        spec_x_mask = np.isnan(x_flat) | (x_flat < 0) | np.isinf(x_flat)
        mu = mu.copy()
        phi = phi.copy()
        mu[spec_x_mask] = 1.0
        phi[spec_x_mask] = 1.0
        mu[phi == np.inf] = 1.0
        phi[mu == 0.0] = 1.0

        left_limit = (
            (x_flat < 0)
            | ((x_flat == 0) & (mu > 0) & (phi < np.inf))
            | ((x_flat < mu) & (phi == 0))
        )
        right_limit = (
            ((x_flat > mu) & ((mu == 0) | (phi == 0)))
            | np.isinf(x_flat)
            | ((x_flat > 0) & (phi == np.inf))
        )
        spike = ((x_flat == mu) & ((mu == 0) | (phi == 0))) | (
            (x_flat == 0) & (phi == np.inf)
        )
        invchisq = (mu == np.inf) & ~(left_limit | right_limit | spike)
        na_cases = (
            np.isnan(x_flat)
            | np.isnan(mu)
            | np.isnan(phi)
            | (mu < 0)
            | (phi < 0)
        )
        left_limit = left_limit & ~na_cases
        right_limit = right_limit & ~na_cases
        spike = spike & ~na_cases
        invchisq = invchisq & ~na_cases

        logd[left_limit] = -np.inf
        logd[right_limit] = -np.inf
        logd[spike] = np.inf
        if np.any(invchisq):
            logd[invchisq] = _dinvgauss_inf_mean(x_flat[invchisq], phi[invchisq])
        logd[na_cases] = np.nan

        ok = ~(left_limit | right_limit | spike | invchisq | na_cases)
        if np.any(ok):
            logd[ok] = _dinvgauss_core(
                x_flat[ok], phi[ok], mu[ok], log=True
            )
    else:
        logd = _dinvgauss_core(x_flat, phi, mu, log=True)

    if log:
        out = logd
    else:
        out = np.exp(logd)

    if preserve_shape:
        return out.reshape(out_shape)
    if out_shape == (n,) and np.asarray(x).ndim == 0 and n == 1:
        return np.float64(out[0])
    return out.reshape(out_shape)
