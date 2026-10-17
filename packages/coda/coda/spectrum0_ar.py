"""Autoregressive spectral density at frequency zero.

Translated from coda 0.19-4.1 ``spectrum0.ar`` in ``R/heidel.R``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

_SQRT_EPS = math.sqrt(float(np.finfo(np.float64).eps))


@dataclass
class Spectrum0Ar:
    """Result of ``spectrum0.ar`` (R list with ``spec`` and ``order``)."""

    spec: np.ndarray
    order: np.ndarray


def spectrum0_ar(x):
    """Estimate the AR spectral density at frequency zero for each column."""
    matrix = _as_matrix(x)
    n_col = matrix.shape[1]
    spec = np.empty(n_col, dtype=np.float64)
    order = np.empty(n_col, dtype=np.int64)
    z = np.arange(1, matrix.shape[0] + 1, dtype=np.float64)
    for column in range(n_col):
        series = matrix[:, column]
        lm_scale = _lm_residual_sd(series, z)
        if lm_scale <= _SQRT_EPS:
            spec[column] = 0.0
            order[column] = 0
        else:
            coefficients, var_pred, fit_order = _yule_walker(series)
            gap = 1.0 - _r_sum(coefficients)
            if gap == 0.0:
                if var_pred > 0.0:
                    spec[column] = math.inf
                elif var_pred < 0.0:
                    spec[column] = -math.inf
                else:
                    spec[column] = math.nan
            else:
                spec[column] = var_pred / (gap * gap)
            order[column] = fit_order
    return Spectrum0Ar(spec=spec, order=order)


def _spectrum0_ar(series):
    """Scalar ``spec`` for one column; used by ``effectiveSize`` and diagnostics."""
    result = spectrum0_ar(series.reshape(-1, 1))
    return float(result.spec[0])


def _as_matrix(value):
    array = np.asarray(value, dtype=np.float64)
    if array.ndim == 0:
        return array.reshape(1, 1)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    if array.ndim == 2:
        return array
    raise ValueError("spectrum0.ar expects a vector or matrix")


def _lm_residual_sd(series, index):
    """``sd(residuals(lm(y ~ index)))`` with ``lm`` NA omission."""
    observed = ~np.isnan(series)
    n_obs = int(np.count_nonzero(observed))
    if n_obs == 0:
        raise ValueError("0 (non-NA) cases")
    if n_obs < 2:
        return math.inf
    y = series[observed]
    z = index[observed]
    design = np.column_stack((np.ones(n_obs, dtype=np.float64), z))
    coef, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ coef
    return math.sqrt(float(np.dot(residual, residual) / (n_obs - 1)))


def _r_mean(series):
    """R's ``mean``: a long-double sum, then one correction pass."""
    n = int(series.size)
    total = np.longdouble(0)
    for value in series:
        total += np.longdouble(value)
    mean = float(total / n)
    carry = np.longdouble(0)
    for value in series:
        carry += np.longdouble(value) - np.longdouble(mean)
    return float(np.longdouble(mean) + carry / n)


def _r_sum(values):
    total = np.longdouble(0)
    for value in values:
        total += np.longdouble(value)
    return float(total)


def _yule_walker(series):
    """Univariate ``stats::ar`` with the default Yule-Walker method and AIC."""
    if np.isnan(series).any():
        raise ValueError("missing values in object")
    n = int(series.size)
    order_max = min(n - 1, math.floor(10.0 * math.log10(n)))
    if order_max < 1:
        raise ValueError("'order.max' must be >= 1")
    centered = series - _r_mean(series)
    covariance = _acf_covariance(centered, order_max)
    if covariance[0] == 0.0:
        raise ValueError("zero-variance series")
    variances, rows = _eureka(covariance)
    penalty = np.arange(order_max + 1, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        aic = n * np.log(variances) + 2.0 * penalty + 2.0
    if not np.any(np.isfinite(aic)):
        raise ValueError("missing values in object")
    fit_order = int(np.nanargmin(aic))
    if fit_order == 0:
        coefficients = np.zeros(0, dtype=np.float64)
    else:
        coefficients = rows[fit_order].copy()
    var_pred = float(variances[fit_order] * n / (n - (fit_order + 1)))
    return coefficients, var_pred, fit_order


def _acf_covariance(series, lag_max):
    """Biased autocovariance, divided by ``n``, after one more demean."""
    series = np.asarray(series, dtype=np.float64)
    series = series - _r_mean(series)
    n = series.size
    covariance = np.empty(lag_max + 1, dtype=np.float64)
    for lag in range(lag_max + 1):
        acc = 0.0
        stop = n - lag
        for index in range(stop):
            acc += float(series[index]) * float(series[index + lag])
        covariance[lag] = acc / n
    return covariance


def _eureka(covariance):
    """R's Fortran ``eureka`` solution of the Yule-Walker equations."""
    rr = [0.0] + [float(value) for value in covariance]
    order_max = covariance.size - 1
    coefficient = [[0.0] * (order_max + 1) for _ in range(order_max + 1)]
    variances = np.empty(order_max + 1, dtype=np.float64)
    auxiliary = [0.0] * (order_max + 4)
    innovation = rr[1]
    cross = rr[2]
    auxiliary[1] = 1.0
    coefficient[1][1] = rr[2] / innovation
    partial_sum = coefficient[1][1] * rr[2]
    variances[0] = rr[1]
    variances[1] = (1.0 - coefficient[1][1] * coefficient[1][1]) * innovation
    for order in range(2, order_max + 1):
        auxiliary[order] = -cross / innovation
        if order > 2:
            half = (order - 2) // 2
            last = half + 1
            for index in range(2, last + 1):
                hold = auxiliary[index]
                mirror = order - index + 1
                auxiliary[index] = auxiliary[index] + auxiliary[order] * auxiliary[mirror]
                auxiliary[mirror] = auxiliary[mirror] + auxiliary[order] * hold
            if 2 * half != order - 2:
                auxiliary[last + 1] = auxiliary[last + 1] * (1.0 + auxiliary[order])
        innovation = innovation + auxiliary[order] * cross
        coefficient[order][order] = (rr[order + 1] - partial_sum) / innovation
        for index in range(1, order):
            coefficient[order][index] = (
                coefficient[order - 1][index]
                + coefficient[order][order] * auxiliary[order - index + 1]
            )
        partial_sum = 0.0
        for index in range(1, order + 1):
            partial_sum += coefficient[order][index] * rr[order + 2 - index]
        variances[order] = variances[order - 1] * (
            1.0 - coefficient[order][order] * coefficient[order][order]
        )
        cross = 0.0
        for index in range(1, order + 1):
            cross += auxiliary[index] * rr[order + 2 - index]
    rows = [np.zeros(0, dtype=np.float64)]
    for order in range(1, order_max + 1):
        rows.append(np.array(coefficient[order][1 : order + 1], dtype=np.float64))
    return variances, rows
