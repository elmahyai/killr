"""Heidelberger and Welch MCMC convergence diagnostic.

Translated from coda 0.19-4.1 ``heidel.diag`` in ``R/heidel.R``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from coda.as_mcmc import as_mcmc, is_mcmc
from coda.as_mcmc_list import _nvar_mcmc, is_mcmc_list
from coda.effectiveSize import _r_mean, _spectrum0_ar
from coda.niter import niter
from coda.varnames import varnames

_COLNAMES = ("stest", "start", "pvalue", "htest", "mean", "halfwidth")


@dataclass
class HeidelDiag:
    """Result of ``heidel_diag`` (R class ``heidel.diag``)."""

    matrix: np.ndarray
    rownames: list[str] | None


def heidel_diag(x, eps=0.1, pvalue=0.05):
    """Stationarity and half-width tests for MCMC mean accuracy."""
    if is_mcmc_list(x):
        return [heidel_diag(chain, eps=eps, pvalue=pvalue) for chain in x]
    chain = as_mcmc(x)
    return _heidel_diag_mcmc(chain, float(eps), float(pvalue))


def _heidel_diag_mcmc(chain, eps, pvalue):
    nvar = _nvar_mcmc(chain)
    names = varnames(chain, allow_null=True)
    if names is None:
        rownames = None
    else:
        rownames = [str(name) for name in names]

    result = np.zeros((nvar, 6), dtype=np.float64)
    for index in range(nvar):
        result[index, :] = _heidel_column(chain, index + 1, eps, pvalue)
    return HeidelDiag(matrix=result, rownames=rownames)


def _heidel_column(chain, column, eps, pvalue):
    series = _mcmc_column(chain, column)
    start_vec = _start_sequence(chain)
    half_start = float(chain.end) / 2.0
    tail = _window_mcmc(series, start=half_start)
    spec0 = _spectrum0_ar(_series_values(tail))
    converged = False
    integral = math.nan
    current = series
    for start in start_vec:
        current = _window_mcmc(series, start=start)
        n = niter(current)
        values = _series_values(current)
        ybar = _r_mean(values)
        bridge = np.cumsum(values) - ybar * np.arange(1, n + 1, dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            bridge_sq = (bridge * bridge) / (n * spec0)
        integral = float(np.sum(bridge_sq) / n)
        if not math.isnan(integral) and _pcramer(integral) < 1.0 - pvalue:
            converged = True
            break

    spec_ci = _spectrum0_ar(_series_values(current))
    n_final = niter(current)
    halfwidth = 1.96 * math.sqrt(spec_ci / n_final) if n_final > 0 else math.nan
    ybar = _r_mean(_series_values(current))
    pvalue_col = (1.0 - _pcramer(integral)) if not math.isnan(integral) else math.nan

    if not converged or math.isnan(integral) or math.isnan(halfwidth):
        return np.array(
            [float(converged), math.nan, pvalue_col, math.nan, math.nan, math.nan]
        )

    passed_hw = abs(halfwidth / ybar) <= eps
    return np.array(
        [
            float(converged),
            float(current.start),
            pvalue_col,
            float(passed_hw),
            ybar,
            halfwidth,
        ]
    )


def _start_sequence(chain):
    start_val = float(chain.start)
    end_half = float(chain.end) / 2.0
    step = niter(chain) / 10.0
    values = []
    current = start_val
    while current <= end_half + 1e-10 * max(abs(end_half), 1.0):
        values.append(current)
        current += step
    return values


def _mcmc_column(chain, column):
    matrix = _chain_matrix(chain)
    if matrix.shape[1] == 1 and np.asarray(chain.data).ndim == 1:
        values = matrix[:, 0]
    else:
        values = matrix[:, column - 1]
    return as_mcmc(values, start=chain.start, end=chain.end, thin=chain.thin)


def _chain_matrix(chain):
    data = np.asarray(chain.data)
    if data.ndim == 1:
        return data.reshape(-1, 1).astype(np.float64, copy=False)
    return np.asarray(data, dtype=np.float64)


def _series_values(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data
    return data[:, 0]


def _mcmc_time(chain):
    count = niter(chain)
    start = float(chain.start)
    step = float(chain.thin)
    return start + np.arange(count, dtype=np.float64) * step


def _window_mcmc(chain, start=None, end=None):
    xstart = float(chain.start)
    xend = float(chain.end)
    xthin = int(round(chain.thin))
    if start is None:
        start = xstart
    else:
        start = float(start)
    if end is None:
        end = xend
    else:
        end = float(end)

    xtime = _mcmc_time(chain)
    ts_eps = float(np.finfo(np.float64).eps) ** 0.75
    if np.all(np.abs(xtime - start) > abs(start) * ts_eps):
        mask = (xtime > start) & ((start + xthin) > xtime)
        start = float(xtime[mask][0])
    if np.all(np.abs(end - xtime) > abs(end) * ts_eps):
        mask = (xtime < end) & ((end - xthin) < xtime)
        end = float(xtime[mask][-1])

    use = np.arange(1, niter(chain) + 1, dtype=np.int64)
    lo = int(math.trunc((start - xstart) / xthin + 1.5))
    hi = int(math.trunc((end - xstart) / xthin + 1.5))
    keep = use[(use >= lo) & (use <= hi)]
    data = _series_values(chain)[keep - 1]
    new_start = xstart + xthin * (lo - 1)
    new_end = xstart + xthin * (hi - 1)
    return as_mcmc(data, start=new_start, end=new_end, thin=float(xthin))


def _pcramer(q, eps=1.0e-5):
    log_eps = math.log(eps)
    if np.isscalar(q):
        values = np.array([float(q)], dtype=np.float64)
    else:
        values = np.asarray(q, dtype=np.float64)
    result = np.zeros(values.shape, dtype=np.float64)
    for index, value in np.ndenumerate(values):
        total = 0.0
        for k in range(4):
            coefficient = (
                math.exp(math.lgamma(k + 0.5))
                * math.sqrt(4 * k + 1)
                / (math.exp(math.lgamma(k + 1)) * math.pi ** 1.5 * math.sqrt(value))
            )
            u = (4 * k + 1) ** 2 / (16.0 * value)
            if u <= -log_eps:
                total += coefficient * math.exp(-u) * _bessel_k_quarter(u)
        result[index] = total
    if np.isscalar(q):
        return float(result[0])
    return result


def _bessel_k_quarter(x):
    if x <= 0.0:
        return math.inf
    if x > 8.0:
        return _bessel_k_quarter_asymptotic(x)
    nu = 0.25
    scale = (math.pi / 2.0) / math.sin(math.pi * nu)
    return scale * (_bessel_i_series(-nu, x) - _bessel_i_series(nu, x))


def _bessel_i_series(nu, x):
    half = x / 2.0
    term = math.exp(nu * math.log(half) - math.lgamma(nu + 1.0))
    total = term
    for k in range(1, 256):
        term *= (half * half) / (k * (nu + k))
        total += term
        if abs(term) <= abs(total) * 1e-16:
            break
    return total


def _bessel_k_quarter_asymptotic(x):
    return math.sqrt(math.pi / (2.0 * x)) * math.exp(-x) * (
        1.0
        - 3.0 / (8.0 * x)
        + 15.0 / (128.0 * x * x)
        - 105.0 / (1024.0 * x * x * x)
    )
