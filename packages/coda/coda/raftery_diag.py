"""Raftery and Lewis MCMC run-length diagnostic.

Translated from coda 0.19-4.1 ``raftery.diag`` in ``R/raftery.R``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from coda.as_mcmc import as_mcmc, is_mcmc
from coda.as_mcmc_list import _nvar_mcmc, is_mcmc_list
from coda.niter import niter
from coda.thin import thin


@dataclass
class RafteryDiag:
    """Result of ``raftery_diag`` (R class ``raftery.diag``)."""

    params: dict[str, float]
    resmatrix: np.ndarray


def raftery_diag(data, q=0.025, r=0.005, s=0.95, converge_eps=0.001):
    """Pilot-run diagnostic for MCMC length, burn-in, and dependence factor."""
    if is_mcmc_list(data):
        return [raftery_diag(chain, q=q, r=r, s=s, converge_eps=converge_eps) for chain in data]
    chain = as_mcmc(data)
    return _raftery_diag_mcmc(chain, q, r, s, converge_eps)


def _raftery_diag_mcmc(chain, q, r, s, converge_eps):
    nvar = _nvar_mcmc(chain)

    phi = _qnorm(0.5 * (1.0 + s))
    nmin = int(math.ceil((q * (1.0 - q) * phi * phi) / (r * r)))
    n_iter = niter(chain)

    if nmin > n_iter:
        resmatrix = np.array(["Error", str(nmin)], dtype=object)
    else:
        resmatrix = np.full((nvar, 4), np.nan, dtype=np.float64)
        matrix = _chain_matrix(chain)
        is_vector = matrix.shape[1] == 1 and np.asarray(chain.data).ndim == 1
        xthin = int(round(thin(chain)))

        for index in range(nvar):
            if is_vector:
                series = matrix[:, 0]
            else:
                series = matrix[:, index]
            quant = _quantile_type7(series, q)
            dichot = as_mcmc(
                series <= quant,
                start=chain.start,
                end=chain.end,
                thin=chain.thin,
            )
            kthin = 0
            bic = 1.0
            testres = None
            while bic >= 0.0:
                kthin += xthin
                testres = _window_mcmc_vector(dichot, thin=kthin)
                newdim = testres.size
                testtran = _transition_table_3(testres)
                g2 = 0.0
                for i1 in range(2):
                    for i2 in range(2):
                        for i3 in range(2):
                            count = testtran[i1, i2, i3]
                            if count != 0.0:
                                fitted = (
                                    (testtran[i1, i2, 0].sum() + testtran[i1, i2, 1].sum())
                                    * (testtran[0, i2, i3].sum() + testtran[1, i2, i3].sum())
                                ) / (testtran[0, i2, :].sum() + testtran[1, i2, :].sum())
                                g2 += count * math.log(count / fitted) * 2.0
                bic = g2 - math.log(newdim - 2) * 2.0

            finaltran = _transition_table_2(testres)
            alpha_denom = finaltran[0, 0] + finaltran[0, 1]
            beta_denom = finaltran[1, 0] + finaltran[1, 1]
            if alpha_denom == 0.0 or beta_denom == 0.0:
                alpha = math.nan
                beta = math.nan
            else:
                alpha = finaltran[0, 1] / alpha_denom
                beta = finaltran[1, 0] / beta_denom
            tempburn = math.log((converge_eps * (alpha + beta)) / max(alpha, beta)) / (
                math.log(abs(1.0 - alpha - beta))
            )
            if not math.isfinite(tempburn):
                nburn = math.nan
            else:
                nburn = float(int(math.ceil(tempburn)) * kthin)
            tempprec = (
                (2.0 - alpha - beta) * alpha * beta * phi * phi
            ) / (((alpha + beta) ** 3) * r * r)
            if not math.isfinite(tempprec):
                nkeep = math.nan
            else:
                nkeep = float(int(math.ceil(tempprec)) * kthin)
            if not math.isfinite(nburn) or not math.isfinite(nkeep):
                iratio = math.nan
            else:
                iratio = (nburn + nkeep) / nmin
            resmatrix[index, 0] = nburn
            resmatrix[index, 1] = nkeep + nburn if math.isfinite(nkeep) and math.isfinite(nburn) else math.nan
            resmatrix[index, 2] = float(nmin)
            resmatrix[index, 3] = _signif(iratio, 3) if math.isfinite(iratio) else math.nan

    return RafteryDiag(
        params={"r": float(r), "s": float(s), "q": float(q)},
        resmatrix=resmatrix,
    )


def _chain_matrix(chain):
    data = np.asarray(chain.data)
    if data.ndim == 1:
        return data.reshape(-1, 1).astype(np.float64, copy=False)
    return np.asarray(data, dtype=np.float64)


def _mcmc_time(chain):
    count = niter(chain)
    start = float(chain.start)
    step = float(chain.thin)
    return start + np.arange(count, dtype=np.float64) * step


def _window_mcmc_vector(chain, thin):
    xstart = float(chain.start)
    xend = float(chain.end)
    xthin = int(round(chain.thin))
    thin_val = int(round(thin))
    if thin_val % xthin != 0:
        thin_val = xthin
    start = xstart
    end = xend
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
    stride = thin_val // xthin
    keep = use[(use >= lo) & (use <= hi) & ((use - lo) % stride == 0)]
    data = np.asarray(chain.data)
    if data.ndim == 1:
        return np.asarray(data[keep - 1], dtype=bool)
    return np.asarray(data[keep - 1, 0], dtype=bool)


def _transition_table_3(series):
    table = np.zeros((2, 2, 2), dtype=np.float64)
    for index in range(series.size - 2):
        i1 = int(bool(series[index]))
        i2 = int(bool(series[index + 1]))
        i3 = int(bool(series[index + 2]))
        table[i1, i2, i3] += 1.0
    return table


def _transition_table_2(series):
    table = np.zeros((2, 2), dtype=np.float64)
    for index in range(series.size - 1):
        i1 = int(bool(series[index]))
        i2 = int(bool(series[index + 1]))
        table[i1, i2] += 1.0
    return table


def _quantile_type7(values, prob):
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    size = ordered.size
    if size == 0:
        return math.nan
    span = max(size - 1, 0)
    position = 1.0 + span * float(prob)
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    result = ordered[lo - 1]
    if position > lo and ordered[hi - 1] != result:
        weight = position - lo
        result = (1.0 - weight) * result + weight * ordered[hi - 1]
    return float(result)


def _signif(x, digits):
    if x == 0.0 or not math.isfinite(x):
        return float(x)
    power = math.floor(math.log10(abs(x)))
    return float(round(x, int(digits - 1 - power)))


def _qnorm(p):
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    x = _acklam(p)
    for _ in range(3):
        err = _pnorm(x) - p
        if err == 0.0:
            break
        density = math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
        step = err / density
        x = x - step / (1.0 + x * step / 2.0)
    return x


def _pnorm(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _acklam(p):
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285084469e02,
        1.383577518672690e02,
        -3.066479861614136e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411952e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982142052e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    plow = 0.02425
    phigh = 1.0 - plow
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if phigh < p:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )
