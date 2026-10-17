"""Impulse responses, forecast-error variance, and residual diagnostics."""

import math

import numpy as np
from scipy.stats import chi2, norm

from .estimate import Acoef, residuals


def Phi(x, nstep=10):
    nstep = abs(int(nstep))
    k = x.K
    p = x.p
    lags = Acoef(x)
    depth = max(nstep + 1, p)
    coeff = np.zeros((k, k, depth))
    for i in range(p):
        coeff[:, :, i] = lags[i]
    phi = np.zeros((k, k, nstep + 1))
    phi[:, :, 0] = np.eye(k)
    if nstep >= 1:
        phi[:, :, 1] = phi[:, :, 0] @ coeff[:, :, 0]
    for i in range(2, nstep + 1):
        acc = phi[:, :, 0] @ coeff[:, :, i - 1]
        for j in range(1, i):
            acc = acc + phi[:, :, j] @ coeff[:, :, i - 1 - j]
        phi[:, :, i] = acc
    return phi


def Psi(x, nstep=10):
    phi = Phi(x, nstep=nstep)
    params = x.datamat.shape[1] - x.K
    sigma = residuals(x).T @ residuals(x) / (x.obs - params)
    factor = np.linalg.cholesky(sigma)
    psi = np.zeros_like(phi)
    for i in range(phi.shape[2]):
        psi[:, :, i] = phi[:, :, i] @ factor
    return psi


def _fecov(x, n_ahead):
    df = x.varresult[x.names[0]]["df_residual"]
    sigma = residuals(x).T @ residuals(x) / df
    out = np.empty((x.K, x.K, n_ahead))
    out[:, :, 0] = sigma
    phi = Phi(x, nstep=n_ahead)
    for i in range(1, n_ahead):
        temp = np.zeros((x.K, x.K))
        for j in range(1, i + 1):
            temp = temp + phi[:, :, j] @ sigma @ phi[:, :, j].T
        out[:, :, i] = temp + out[:, :, 0]
    return out


def fevd(x, n_ahead=10):
    n_ahead = abs(int(n_ahead))
    k = x.K
    mse_y = _fecov(x, n_ahead)
    psi = Psi(x, nstep=n_ahead)
    omega = np.zeros((n_ahead, k, k))
    for i in range(n_ahead):
        mse = np.diag(mse_y[:, :, i])
        temp = np.zeros((k, k))
        for step in range(i + 1):
            temp = temp + psi[:, :, step] ** 2
        temp = temp / mse[:, None]
        omega[i] = temp.T
    return {name: omega[:, :, i] for i, name in enumerate(x.names)}


def irf(x, impulse=None, response=None, n_ahead=10, ortho=True, cumulative=False, boot=False):
    names = x.names
    impulse = list(names) if impulse is None else list(impulse)
    response = list(names) if response is None else list(response)
    if boot:
        raise ValueError("bootstrap intervals use R's RNG; call irf with boot=False")
    series = Psi(x, nstep=n_ahead) if ortho else Phi(x, nstep=n_ahead)
    out = {}
    response_index = [names.index(name) for name in response]
    for name in impulse:
        column = names.index(name)
        block = series[response_index, column, : n_ahead + 1].T
        if cumulative:
            block = np.cumsum(block, axis=0)
        out[name] = block
    return out


def _center_scale(resid):
    center = resid.mean(axis=0)
    scale = resid.std(axis=0, ddof=1)
    return (resid - center) / scale


def arch_test(x, lags_single=16, lags_multi=5, multivariate_only=True):
    resid = residuals(x)
    scaled = _center_scale(resid)
    k = x.K
    obs = x.obs
    cols = k * (k + 1) // 2
    vech = np.empty((obs, cols))
    for i in range(obs):
        outer = np.outer(scaled[i], scaled[i])
        vech[i] = outer[np.tril_indices(k)]
    width = lags_multi + 1
    embedded = _embed_rows(vech, width)
    y = embedded[:, :cols]
    design = np.column_stack([np.ones(y.shape[0]), embedded[:, cols:]])
    _c0, r0, _f0 = _ols(np.ones((y.shape[0], 1)), y)
    _c1, r1, _f1 = _ols(design, y)
    omega0 = np.cov(r0, rowvar=False, ddof=1)
    omega1 = np.cov(r1, rowvar=False, ddof=1)
    r2 = 1 - (2 / (k * (k + 1))) * np.trace(omega1 @ np.linalg.solve(omega0, np.eye(omega0.shape[0])))
    n = r1.shape[0]
    statistic = 0.5 * n * k * (k + 1) * r2
    df = lags_multi * k ** 2 * (k + 1) ** 2 / 4
    pvalue = float(chi2.sf(statistic, df))
    return {"statistic": float(statistic), "parameter": df, "p_value": pvalue}


def _ols(design, response):
    coef, _r, _rank, _sv = np.linalg.lstsq(design, response, rcond=None)
    fitted = design @ coef
    return coef, response - fitted, fitted


def _embed_rows(values, dimension):
    rows = values.shape[0] - dimension + 1
    width = values.shape[1]
    out = np.empty((rows, dimension * width))
    for lag in range(dimension):
        out[:, lag * width:(lag + 1) * width] = values[(dimension - 1 - lag):(values.shape[0] - lag)]
    return out


def serial_test(x, lags_pt=16, type="PT.asymptotic"):
    resids = residuals(x)
    k = x.K
    obs = x.obs
    c0 = resids.T @ resids / obs
    c0inv = np.linalg.solve(c0, np.eye(k))
    traces = []
    for lag in range(1, lags_pt + 1):
        earlier = resids[:-lag]
        later = resids[lag:]
        # .matlag1 prepends NA then drops the tail, then drops the first lag rows.
        # The remaining pairs are resids[lag:] with resids[:-lag].
        ci = later.T @ earlier / obs
        traces.append(np.trace(ci.T @ c0inv @ ci @ c0inv))
    traces = np.array(traces)
    qh = obs * np.sum(traces)
    adjust = obs - np.arange(1, lags_pt + 1)
    qh_star = obs ** 2 * np.sum(traces / adjust)
    df = k ** 2 * lags_pt - k ** 2 * x.p
    statistic = qh if type == "PT.asymptotic" else qh_star
    return {"statistic": float(statistic), "parameter": df, "p_value": float(chi2.sf(statistic, df))}


def BQ(x):
    lags = Acoef(x)
    ident = np.eye(x.K)
    mat1 = ident - sum(lags)
    mat2 = ident - sum(block.T for block in lags)
    df = x.varresult[x.names[0]]["df_residual"]
    sigma = residuals(x).T @ residuals(x) / df
    long_run = np.linalg.solve(mat1, sigma) @ np.linalg.inv(mat2)
    lrim = np.linalg.cholesky(long_run)
    return {"A": ident, "B": mat1 @ lrim, "LRIM": lrim, "Sigma_U": sigma * 100}


def predict(x, n_ahead=10, ci=0.95):
    """Point forecast and normal interval. Seasonal and exogenous terms are not supplied here."""
    n_ahead = int(n_ahead)
    k = x.K
    p = x.p
    coef = x.coefficients
    if x.type == "const":
        det = np.ones((n_ahead, 1))
    elif x.type == "trend":
        start = x.obs + 1 + p
        det = np.arange(start, start + n_ahead, dtype=float).reshape(-1, 1)
    elif x.type == "both":
        start = x.obs + 1 + p
        det = np.column_stack([np.ones(n_ahead), np.arange(start, start + n_ahead, dtype=float)])
    else:
        det = None
    sigma = _fecov(x, n_ahead)
    half = -norm.ppf((1 - ci) / 2) * np.sqrt(np.array([np.diag(sigma[:, :, i]) for i in range(n_ahead)]))
    zy = x.datamat[:, : k * (p + 1)]
    last = zy[-1].copy()
    forecast = np.empty((n_ahead, k))
    for i in range(n_ahead):
        lags = last[: k * p]
        row = lags if det is None else np.concatenate([lags, det[i]])
        forecast[i] = coef @ row
        last = np.concatenate([forecast[i], last])
    return {"fcst": forecast, "lower": forecast - half, "upper": forecast + half, "ci": half, "model": x}


def normality_test(x):
    resid = residuals(x)
    centered = resid - resid.mean(axis=0)
    obs = x.obs
    k = x.K
    factor = np.linalg.cholesky(centered.T @ centered / obs)
    standard = centered @ np.linalg.solve(factor.T, np.eye(k))
    # R uses chol upper, solve(P) with P = t(chol) is lower. x %*% solve(P).
    # numpy cholesky is lower, matching t(chol). solve(P) is inv(lower).
    b1 = np.sum(standard ** 3, axis=0) / obs
    b2 = np.sum(standard ** 4, axis=0) / obs
    s3 = obs * float(b1 @ b1) / 6
    s4 = obs * float((b2 - 3) @ (b2 - 3)) / 24
    statistic = s3 + s4
    return {
        "statistic": float(statistic),
        "parameter": 2 * k,
        "p_value": float(chi2.sf(statistic, 2 * k)),
        "skewness": s3,
        "kurtosis": s4,
    }
