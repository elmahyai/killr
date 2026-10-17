"""Estimate spectral density at frequency zero.

Translated from coda 0.19-4.1 ``spectrum0`` and ``do.spectrum0`` in ``R/heidel.R``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

_SQRT3 = math.sqrt(3.0)
_SQRT5 = math.sqrt(5.0)
_DBL_EPS = float(np.finfo(np.float64).eps)
_GLM_EPSILON = 1e-8
_GLM_MAXIT = 25


@dataclass
class Spectrum0:
    """Result of ``spectrum0`` (R list with component ``spec``)."""

    spec: np.ndarray


def spectrum0(x, max_freq=0.5, order=1, max_length=200):
    """Estimate the spectral density at frequency zero for each column."""
    matrix = _as_matrix(x)
    batch_size = 1
    if max_length is not None and matrix.shape[0] > max_length:
        batch_size = int(math.ceil(matrix.shape[0] / max_length))
        matrix = _aggregate_batch_means(matrix, batch_size)
    out = _do_spectrum0(matrix, max_freq=max_freq, order=order)
    out.spec = out.spec * batch_size
    return out


def _as_matrix(value):
    array = np.asarray(value, dtype=np.float64)
    if array.ndim == 0:
        return array.reshape(1, 1)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    if array.ndim == 2:
        return array
    raise ValueError("spectrum0 expects a vector or matrix")


def _aggregate_batch_means(matrix, batch_size):
    n_row = matrix.shape[0]
    n_batch = n_row // batch_size
    if n_batch == 0:
        raise ValueError("no complete batches after aggregation")
    trimmed = matrix[: n_batch * batch_size, :]
    reshaped = trimmed.reshape(n_batch, batch_size, matrix.shape[1])
    return reshaped.mean(axis=1)


def _do_spectrum0(matrix, max_freq=0.5, order=1):
    del max_freq  # default 0.5 includes every frequency R keeps in the periodogram
    if order not in (0, 1, 2):
        raise ValueError("invalid order")
    n_row = matrix.shape[0]
    n_freq = n_row // 2
    freq = np.arange(1, n_freq + 1, dtype=np.float64) / n_row
    f1 = _SQRT3 * (4.0 * freq - 1.0)
    f2 = _SQRT5 * (24.0 * freq * freq - 12.0 * freq + 1.0)
    spec_out = np.zeros(matrix.shape[1], dtype=np.float64)
    for column in range(matrix.shape[1]):
        series = matrix[:, column]
        if _r_var(series) == 0.0:
            spec_out[column] = 0.0
            continue
        yfft = np.fft.fft(series)
        periodogram = np.real(yfft * np.conj(yfft)) / n_row
        spec_values = periodogram[1 : n_freq + 1]
        if order == 0:
            design = np.column_stack((np.ones(n_freq, dtype=np.float64),))
            predict_row = np.array([1.0], dtype=np.float64)
        elif order == 1:
            design = np.column_stack((np.ones(n_freq, dtype=np.float64), f1))
            predict_row = np.array([1.0, -_SQRT3], dtype=np.float64)
        else:
            design = np.column_stack((np.ones(n_freq, dtype=np.float64), f1, f2))
            predict_row = np.array([1.0, -_SQRT3, _SQRT5], dtype=np.float64)
        coefficients = _gamma_log_glm(design, spec_values)
        eta = float(predict_row @ coefficients)
        spec_out[column] = math.exp(eta)
    return Spectrum0(spec=spec_out)


def _r_var(series):
    n = series.size
    if n < 2:
        return math.nan
    mean = float(np.sum(series, dtype=np.float64) / n)
    total = 0.0
    for value in series:
        delta = float(value) - mean
        total += delta * delta
    return total / (n - 1)


def _gamma_log_glm(design, response):
    """R ``stats::glm.fit`` with ``Gamma(link='log')``."""
    y = np.asarray(response, dtype=np.float64)
    design = np.asarray(design, dtype=np.float64)
    mu = np.asarray(y + 1e-4, dtype=np.longdouble)
    eta = np.log(mu)
    devold = float(np.sum(_gamma_deviance(y, np.asarray(mu, dtype=np.float64))))
    coef = np.zeros(design.shape[1], dtype=np.float64)
    eps = np.longdouble(_DBL_EPS)
    for _ in range(_GLM_MAXIT):
        mu_eta_val = np.maximum(np.exp(eta), eps)
        z = eta + (np.longdouble(y) - mu) / mu_eta_val
        w = np.sqrt((mu_eta_val * mu_eta_val) / (mu * mu))
        xw = design * np.asarray(w, dtype=np.float64)[:, None]
        zw = np.asarray(z * w, dtype=np.float64)
        coef = _qr_coef(xw, zw)
        eta = np.longdouble(design) @ np.longdouble(coef)
        mu = np.exp(eta)
        dev = float(np.sum(_gamma_deviance(y, np.asarray(mu, dtype=np.float64))))
        if abs(dev - devold) / (0.1 + abs(dev)) < _GLM_EPSILON:
            return coef
        devold = dev
    return coef


def _gamma_deviance(y, mu):
    mu = np.clip(mu, 1e-12, None)
    out = np.empty_like(y, dtype=np.float64)
    for index, (value, mean) in enumerate(zip(y, mu)):
        if value == 0.0:
            ratio = 1.0
        else:
            ratio = value / mean
        out[index] = -2.0 * (math.log(ratio) - (value - mean) / mean)
    return out


def _qr_coef(design, response):
    q, r = np.linalg.qr(design, mode="reduced")
    return np.linalg.solve(r, q.T @ response)
