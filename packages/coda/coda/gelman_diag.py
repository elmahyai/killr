"""Gelman and Rubin MCMC convergence diagnostic.

Translated from coda 0.19-4.1 ``gelman.diag`` in ``R/gelman.R``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from coda.as_mcmc import Mcmc, as_mcmc
from coda.as_mcmc_list import McmcList, _nvar_mcmc, as_mcmc_list
from coda.niter import niter
from coda.varnames import varnames


@dataclass
class GelmanDiag:
    """Result of ``gelman_diag`` (R class ``gelman.diag``)."""

    psrf: np.ndarray
    mpsrf: float | None
    psrf_colnames: tuple[str, str] = ("Point est.", "Upper C.I.")
    psrf_rownames: list[str] | None = None


def gelman_diag(
    x,
    confidence=0.95,
    transform=False,
    autoburnin=True,
    multivariate=True,
):
    """Potential scale reduction factors for parallel MCMC chains."""
    mlist = as_mcmc_list(x)
    if len(mlist.chains) < 2:
        raise ValueError("You need at least two chains")

    if autoburnin:
        chain_start = float(mlist.chains[0].start)
        chain_end = float(mlist.chains[0].end)
        if chain_start < chain_end / 2.0:
            mlist = _window_mcmc_list(mlist, start=chain_end / 2.0 + 1.0)

    n_iter = niter(mlist)
    n_chain = len(mlist.chains)
    n_var = _nvar_mcmc(mlist.chains[0])
    xnames = varnames(mlist, allow_null=True)

    if transform:
        mlist = _gelman_transform(mlist)

    matrices = [_as_matrix(chain) for chain in mlist.chains]
    s2 = np.stack([np.cov(mat, rowvar=False, bias=False) for mat in matrices], axis=2)
    w_mat = np.mean(s2, axis=2)
    xbar = np.column_stack([np.mean(mat, axis=0) for mat in matrices])
    b_mat = n_iter * np.cov(xbar, bias=False)

    mpsrf = None
    if n_var > 1 and multivariate:
        emax = _max_eigen_w_inv_b(w_mat, b_mat)
        mpsrf = math.sqrt((1.0 - 1.0 / n_iter) + (1.0 + 1.0 / n_var) * emax / n_iter)

    w = np.diag(w_mat)
    b = np.diag(b_mat)
    s2_diag = np.column_stack([np.diag(s2[:, :, chain_index]) for chain_index in range(n_chain)])
    muhat = np.mean(xbar, axis=1)
    var_w = np.var(s2_diag, axis=1, ddof=1) / n_chain
    var_b = (2.0 * b * b) / (n_chain - 1.0)
    cov_s2_xbar2 = _matrix_column_covariance(s2_diag, xbar * xbar)
    cov_s2_xbar = _matrix_column_covariance(s2_diag, xbar)
    cov_wb = (n_iter / n_chain) * np.diag(
        cov_s2_xbar2 - 2.0 * muhat[:, np.newaxis] * cov_s2_xbar
    )

    v = (n_iter - 1.0) * w / n_iter + (1.0 + 1.0 / n_chain) * b / n_iter
    var_v = (
        (n_iter - 1.0) ** 2 * var_w
        + (1.0 + 1.0 / n_chain) ** 2 * var_b
        + 2.0 * (n_iter - 1.0) * (1.0 + 1.0 / n_chain) * cov_wb
    ) / (n_iter**2)
    df_v = (2.0 * v * v) / var_v

    df_adj = (df_v + 3.0) / (df_v + 1.0)
    b_df = n_chain - 1.0
    w_df = (2.0 * w * w) / var_w
    r2_fixed = (n_iter - 1.0) / n_iter
    r2_random = (1.0 + 1.0 / n_chain) * (1.0 / n_iter) * (b / w)
    r2_estimate = r2_fixed + r2_random
    f_quantile = _qf((1.0 + confidence) / 2.0, b_df, w_df)
    r2_upper = r2_fixed + f_quantile * r2_random
    psrf = np.column_stack(
        (
            np.sqrt(df_adj * r2_estimate),
            np.sqrt(df_adj * r2_upper),
        )
    )
    return GelmanDiag(psrf=psrf, mpsrf=mpsrf, psrf_rownames=xnames)


def _as_matrix(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data


def _window_mcmc_list(mlist, start=None, end=None):
    chains = [_window_mcmc(chain, start=start, end=end) for chain in mlist.chains]
    return McmcList(chains=chains)


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
    data = _as_matrix(chain)[keep - 1]
    new_start = xstart + xthin * (lo - 1)
    new_end = xstart + xthin * (hi - 1)
    return as_mcmc(data, start=new_start, end=new_end, thin=float(xthin))


def _gelman_transform(mlist):
    chains = []
    for chain in mlist.chains:
        chains.append(_gelman_transform_chain(chain))
    return McmcList(chains=chains)


def _gelman_transform_chain(chain):
    mat = _as_matrix(chain).copy()
    n_var = mat.shape[1]
    if n_var == 1:
        column = mat[:, 0]
        if np.min(column) > 0.0:
            if np.max(column) < 1.0:
                mat[:, 0] = np.log(column / (1.0 - column))
            else:
                mat[:, 0] = np.log(column)
    else:
        for index in range(n_var):
            column = mat[:, index]
            if np.min(column) > 0.0:
                if np.max(column) < 1.0:
                    mat[:, index] = np.log(column / (1.0 - column))
                else:
                    mat[:, index] = np.log(column)
    return Mcmc(data=mat, start=chain.start, end=chain.end, thin=chain.thin)


def _matrix_column_covariance(x, y):
    n_var = x.shape[0]
    result = np.empty((n_var, n_var), dtype=np.float64)
    x_t = x.T
    y_t = y.T
    for left in range(n_var):
        for right in range(n_var):
            result[left, right] = np.cov(x_t[:, left], y_t[:, right], ddof=1)[0, 1]
    return result


def _max_eigen_w_inv_b(w_mat, b_mat):
    upper = np.linalg.cholesky(w_mat).T
    lower = upper.T
    temp = np.linalg.solve(lower, b_mat)
    matrix = np.linalg.solve(lower, temp.T)
    sym = 0.5 * (matrix + matrix.T)
    values = np.linalg.eigvalsh(sym)
    return float(values[-1])


def _qf(probability, df1, df2):
    prob, d1, d2 = np.broadcast_arrays(
        np.asarray(probability, dtype=np.float64),
        np.asarray(df1, dtype=np.float64),
        np.asarray(df2, dtype=np.float64),
    )
    result = np.empty(prob.shape, dtype=np.float64)
    flat_prob = prob.ravel()
    flat_d1 = d1.ravel()
    flat_d2 = d2.ravel()
    flat_out = result.ravel()
    for index in range(flat_out.size):
        flat_out[index] = _qf_scalar(
            float(flat_prob[index]),
            float(flat_d1[index]),
            float(flat_d2[index]),
        )
    if np.isscalar(probability) and np.isscalar(df1) and np.isscalar(df2):
        return float(result)
    return result


def _qf_scalar(probability, df1, df2):
    if not math.isfinite(probability) or not math.isfinite(df1) or not math.isfinite(df2):
        return math.nan
    if df1 <= 0.0 or df2 <= 0.0:
        return math.nan
    lo = 0.0
    hi = 1.0
    while 1.0 - _pf_survival(hi, df1, df2) < probability:
        hi *= 2.0
        if not math.isfinite(hi):
            return math.nan
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if 1.0 - _pf_survival(mid, df1, df2) < probability:
            lo = mid
        else:
            hi = mid
        if hi - lo <= abs(hi) * 1e-14 + 1e-16:
            break
    return (lo + hi) / 2.0


def _pf_survival(stat, df1, df2):
    if not math.isfinite(stat):
        return math.nan
    x = df2 / (df2 + df1 * stat)
    return _betainc(df2 / 2.0, df1 / 2.0, x)


def _betainc(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    front = math.exp(ln)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _betacf(a, b, x):
    max_iterations = 2000
    epsilon = 3.0e-14
    am = 1.0
    bm = 1.0
    az = 1.0
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    bz = 1.0 - qab * x / qap
    if abs(bz) < epsilon:
        bz = epsilon
    em = 0
    tem = 0.0
    d = 0.0
    ap = 0.0
    bp = 0.0
    app = 0.0
    bpp = 0.0
    aold = 0.0
    for _ in range(max_iterations):
        em += 1
        tem = em + em
        d = em * (b - em) * x / ((qam + tem) * (a + tem))
        ap = az + d * am
        bp = bz + d * bm
        d = -(a + em) * (qab + em) * x / ((a + tem) * (qap + tem))
        app = ap + d * az
        bpp = bp + d * bz
        am = ap / bpp
        bm = bp / bpp
        az = app / bpp
        bz = 1.0
        if abs(az - aold) < epsilon * max(abs(az), 1.0):
            return az
        aold = az
    if math.isfinite(az):
        return az
    raise RuntimeError("betacf failed to converge")
