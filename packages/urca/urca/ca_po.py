"""Phillips-Ouliaris cointegration test (``ca.po``)."""

from __future__ import annotations

import math

import numpy as np
from scipy.linalg import qr

from urca.tests import _match

_PZ_CVALS = np.array(
    [
        33.9267,
        62.1436,
        99.2664,
        143.0775,
        195.6202,
        40.8217,
        71.2751,
        109.7426,
        155.8019,
        210.2910,
        55.1911,
        89.6679,
        131.5716,
        180.4845,
        237.7723,
        47.5877,
        80.2034,
        120.3035,
        168.8572,
        225.2303,
        55.2202,
        89.7619,
        132.2207,
        182.0749,
        241.3316,
        71.9273,
        109.4525,
        153.4504,
        209.8054,
        270.5018,
        71.9586,
        113.4929,
        163.1050,
        219.5098,
        284.0100,
        81.3812,
        124.3933,
        175.9902,
        234.2865,
        301.0949,
        102.0167,
        145.8644,
        201.0905,
        264.4988,
        335.9054,
    ],
    dtype=float,
).reshape((5, 3, 3), order="F")

_PU_CVALS = np.array(
    [
        20.3933,
        26.7022,
        33.5359,
        39.2826,
        44.3725,
        25.9711,
        32.9392,
        40.1220,
        46.2691,
        51.8614,
        38.3413,
        46.4097,
        55.7341,
        63.2149,
        69.4939,
        27.8536,
        33.6955,
        39.6949,
        45.3308,
        50.3537,
        33.713,
        40.5252,
        46.7281,
        53.2502,
        57.7855,
        48.0021,
        53.8731,
        63.4128,
        71.5214,
        76.7705,
        41.2488,
        46.1061,
        52.0015,
        57.3667,
        61.6155,
        48.8439,
        53.8300,
        60.2384,
        65.8706,
        70.7416,
        65.1714,
        69.2629,
        78.3470,
        84.5480,
        91.0392,
    ],
    dtype=float,
).reshape((5, 3, 3), order="F")


class CaPo:
    """Slots of an S4 ``ca.po`` object."""

    def __init__(self, **slots):
        self.__dict__.update(slots)

    def __str__(self):
        return f"{self.test_name}\n\n{self.type}-statistic {self.teststat:.6g}\n"


def ca_po(z, demean="none", lag="short", type="Pu", tol=None):
    """Phillips-Ouliaris cointegration test."""
    matrix = _as_matrix(z)
    if matrix.shape[1] < 2 or matrix.shape[1] > 6:
        raise ValueError("Please provide a matrix with at least two and maximal six columns")
    demean = _match(demean, ("none", "constant", "trend"))
    lag = _match(lag, ("short", "long"))
    kind = _match(type, ("Pu", "Pz"))
    nobs = matrix.shape[0]
    m = matrix.shape[1]
    zl = matrix[1:nobs, :]
    zr = matrix[0 : nobs - 1, :]
    nobs = nobs - 1
    if lag == "short":
        lmax = math.trunc(4 * (nobs / 100) ** 0.25)
    else:
        lmax = math.trunc(12 * (nobs / 100) ** 0.25)
    if demean == "none":
        ari3 = 1
        model = "none"
        res = _mlm_residuals(zl, zr, intercept=False)
        if kind == "Pu":
            resu = _ols_univariate(matrix[:, 0], matrix[:, 1:], intercept=False)["residuals"]
            test_reg = _mlm_summary(matrix[:, 0], matrix[:, 1:], intercept=False)
        else:
            test_reg = _mlm_summary(zl, zr, intercept=False)
    elif demean == "constant":
        ari3 = 2
        model = "with constant only"
        res = _mlm_residuals(zl, zr, intercept=True)
        if kind == "Pu":
            resu = _ols_univariate(matrix[:, 0], matrix[:, 1:], intercept=True)["residuals"]
            test_reg = _mlm_summary(matrix[:, 0], matrix[:, 1:], intercept=True)
        else:
            test_reg = _mlm_summary(zl, zr, intercept=True)
    else:
        ari3 = 3
        model = "with constant and linear trend"
        trd = np.arange(1, nobs + 1, dtype=float)
        res = _mlm_residuals(zl, zr, intercept=True, trend=trd)
        if kind == "Pu":
            trd_full = np.arange(1, nobs + 2, dtype=float)
            resu = _ols_univariate(matrix[:, 0], matrix[:, 1:], intercept=True, trend=trd_full)[
                "residuals"
            ]
            test_reg = _mlm_summary(matrix[:, 0], matrix[:, 1:], intercept=True, trend=trd_full)
        else:
            test_reg = _mlm_summary(zl, zr, intercept=True, trend=trd)
    xi2 = (res.T @ res) / nobs
    smat = np.zeros((m, m), dtype=float)
    if lmax > 0:
        weights = 1 - np.arange(1, lmax + 1, dtype=float) / (lmax + 1)
        for index, weight in enumerate(weights, start=1):
            top = res[index:, :]
            bottom = res[: nobs - index, :]
            smat += weight * (top.T @ bottom + bottom.T @ top)
    omega = xi2 + smat / nobs
    if kind == "Pz":
        mzz = (zl.T @ zl) / nobs
        mzzinv = _solve(mzz, tol)
        teststat = float(nobs * np.trace(omega @ mzzinv))
        row = _PZ_CVALS[m - 2, :, ari3 - 1]
        cval = np.array([row], dtype=float)
        out_res = res
    else:
        w11 = float(omega[0, 0])
        w21 = omega[1:, 0]
        o22inv = _solve(omega[1:, 1:], tol)
        w112 = w11 - float(w21.T @ o22inv @ w21)
        ssqr = float(np.dot(resu, resu)) / nobs
        teststat = float(nobs * w112 / ssqr)
        row = _PU_CVALS[m - 2, :, ari3 - 1]
        cval = np.array([row], dtype=float)
        out_res = np.asarray(resu, dtype=float).reshape(-1, 1)
    return CaPo(
        z=matrix,
        type=kind,
        model=model,
        lag=int(lmax),
        cval=cval,
        res=out_res,
        teststat=teststat,
        testreg=test_reg,
        test_name="Phillips and Ouliaris",
    )


def _as_matrix(z):
    array = np.asarray(z, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    keep = ~np.any(np.isnan(array), axis=1)
    return array[keep, :]


def _design(zr, intercept, trend=None):
    parts = []
    if intercept:
        parts.append(np.ones(zr.shape[0]))
    parts.append(zr)
    if trend is not None:
        parts.append(np.asarray(trend, dtype=float).reshape(-1))
    if len(parts) == 1:
        return parts[0].reshape(-1, 1) if parts[0].ndim == 1 else parts[0]
    return np.column_stack(parts)


def _mlm_residuals(y, zr, intercept, trend=None):
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    design = _design(zr, intercept, trend)
    n, p = design.shape
    q, r, pivot = qr(design, mode="economic", pivoting=True)
    tol = np.finfo(float).eps * max(n, p) * np.max(np.abs(np.diag(r)))
    rank = int(np.sum(np.abs(np.diag(r)) > tol))
    piv = pivot[:rank]
    r1 = r[:rank, :rank]
    coef_p = np.linalg.solve(r1, q.T @ y)
    coef = np.zeros((p, y.shape[1]))
    coef[piv, :] = coef_p
    return y - design @ coef


def _mlm_summary(y, zr, intercept, trend=None):
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    design = _design(zr, intercept, trend)
    summaries = []
    for column in range(y.shape[1]):
        fit = _r_lm(y[:, column], design)
        summaries.append(
            {
                "coefficients": np.column_stack(
                    (fit["coef"], fit["se"], fit["t"], _pt(fit["t"], fit["df"]))
                )
            }
        )
    return summaries


def _ols_univariate(y, zr, intercept, trend=None):
    design = _design(zr, intercept, trend)
    return _r_lm(np.asarray(y, dtype=float).ravel(), design)


def _r_lm(response, design):
    """Least squares with R ``lm`` rank handling (QR pivoting)."""
    response = np.asarray(response, dtype=float).ravel()
    n, p = design.shape
    if p == 0:
        residuals = response.copy()
        return {
            "coef": np.array([]),
            "se": np.array([]),
            "t": np.array([]),
            "residuals": residuals,
            "df": n,
        }
    q, r, pivot = qr(design, mode="economic", pivoting=True)
    tol = np.finfo(float).eps * max(n, p) * np.max(np.abs(np.diag(r)))
    rank = int(np.sum(np.abs(np.diag(r)) > tol))
    piv = pivot[:rank]
    r1 = r[:rank, :rank]
    qt_y = q.T @ response
    coef_p = np.linalg.solve(r1, qt_y[:rank])
    coef = np.zeros(p)
    coef[piv] = coef_p
    residuals = response - design @ coef
    df = n - rank
    sigma2 = float(np.dot(residuals, residuals)) / df
    rinv = np.linalg.inv(r1)
    cov = np.zeros((p, p))
    cov[np.ix_(piv, piv)] = sigma2 * (rinv @ rinv.T)
    se = np.sqrt(np.diag(cov))
    with np.errstate(divide="ignore", invalid="ignore"):
        tstats = coef / se
    return {
        "coef": coef,
        "se": se,
        "t": tstats,
        "residuals": residuals,
        "df": df,
    }


def _solve(matrix, tol):
    del tol
    return np.linalg.inv(matrix)


def _pt(t_values, df):
    """Two-sided p-values like R ``summary.lm`` ``Pr(>|t|)``."""
    out = []
    for value in np.asarray(t_values, dtype=float).ravel():
        out.append(2.0 * _pt_lower(-abs(value), df))
    return np.asarray(out, dtype=float)


def _pt_lower(value, df):
    x = df / (df + value * value)
    prob = 0.5 * _betainc(df / 2, 0.5, x)
    if value < 0:
        return prob
    return 1.0 - prob


def _betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1 - x) - ln_beta) / a
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x)
    tail = math.exp(b * math.log(1 - x) + a * math.log(x) - ln_beta) / b
    return 1.0 - tail * _betacf(b, a, 1 - x)


def _betacf(a, b, x):
    max_iter = 200
    eps = 3e-14
    am = 1.0
    bm = 1.0
    az = 1.0
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    bz = 1.0 - qab * x / qap
    for index in range(1, max_iter + 1):
        em = float(index)
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
        if abs(bz) < eps:
            bz = eps
        if abs(az - app / bpp) < eps * abs(az):
            return az
    return az
