"""Unit-root, nonlinearity, and normality tests from tseries."""

from __future__ import annotations

import math
import warnings

import numpy as np

from tseries._num import (
    approx,
    critical_p,
    embed,
    htest,
    lm,
    match_arg,
    ones,
    pchisq_sf,
    pf_sf,
    pnorm,
    pp_sum,
    prcomp_scores,
    r_scale,
)


def _vector(x, label="x"):
    values = np.asarray(x, dtype=float)
    if values.ndim == 2 and values.shape[1] == 1:
        values = values.reshape(-1)
    if values.ndim != 1:
        raise ValueError(f"{label} is not a vector or univariate time series")
    if np.isnan(values).any():
        raise ValueError(f"NAs in {label}")
    return values


def runs_test(x, alternative="two.sided"):
    labels = [str(item) for item in x]
    if any(item == "NA" or item == "nan" for item in labels):
        raise ValueError("NAs in x")
    levels = list(dict.fromkeys(labels))
    if len(levels) != 2:
        raise ValueError("x does not contain dichotomous data")
    alternative = match_arg(alternative, ("two.sided", "less", "greater"))
    changes = sum(left != right for left, right in zip(labels[1:], labels[:-1]))
    runs = 1 + changes
    n1 = sum(item == levels[0] for item in labels)
    n2 = sum(item == levels[1] for item in labels)
    total = n1 + n2
    mean = 1 + 2 * n1 * n2 / total
    scale = math.sqrt(
        2 * n1 * n2 * (2 * n1 * n2 - n1 - n2) / (total**2 * (total - 1))
    )
    stat = (runs - mean) / scale
    if alternative == "two.sided":
        p_value = 2 * pnorm(-abs(stat))
    elif alternative == "less":
        p_value = pnorm(stat)
    else:
        p_value = pnorm(stat, lower_tail=False)
    return htest(
        statistic=stat,
        parameter=None,
        alternative=alternative,
        p_value=p_value,
        method="Runs Test",
    )


def _bds_ck(x, m, eps):
    n = len(x)
    remove = m - 1
    nobs = n - remove
    count = 0
    phi = 0
    for i in range(n):
        if i >= nobs:
            tcount = 0
        else:
            tcount = 0
            xi = x[i]
            for j in range(nobs):
                if abs(xi - x[j]) <= eps:
                    tcount += 1
        count += tcount
        phi += tcount * tcount
    count -= nobs
    phi = phi - nobs - 3 * count
    denom = nobs * (nobs - 1)
    k = phi / (denom * (nobs - 2))
    c1 = count / denom
    cs = [None, c1]
    for dim in range(2, m + 1):
        pairs = 0
        for i in range(nobs):
            for j in range(i + 1, nobs):
                close = True
                for lag in range(dim):
                    if abs(x[i + lag] - x[j + lag]) > eps:
                        close = False
                        break
                if close:
                    pairs += 1
        cs.append(2 * pairs / denom)
    return k, cs, nobs


def _ipow(base, power):
    value = 1.0
    for _ in range(power):
        value *= base
    return value


def _cstat(c, cm, k, m, n):
    sigma = 0.0
    for j in range(1, m):
        sigma += 2.0 * _ipow(k, m - j) * _ipow(c, 2 * j)
    sigma += _ipow(k, m) + (m - 1) * (m - 1) * _ipow(c, 2 * m) - m * m * k * _ipow(c, 2 * m - 2)
    sigma *= 4.0
    std = math.sqrt(sigma / n)
    return (cm - _ipow(c, m)) / std


def bds_test(x, m=3, eps=None, trace=False):
    series = _vector(x)
    m = int(m)
    if m < 2:
        raise ValueError("m is less than 2")
    if eps is None:
        scale = float(series.std(ddof=1))
        eps = np.linspace(0.5 * scale, 2 * scale, 4)
    eps = np.asarray(eps, dtype=float).reshape(-1)
    if len(eps) == 0 or np.any(eps <= 0):
        raise ValueError("invalid eps")
    stats = np.zeros((m - 1, len(eps)))
    for col, width in enumerate(eps):
        _k, cs, _nobs = _bds_ck(series, m, float(width))
        nobs = len(series) - m + 1
        for dim in range(2, m + 1):
            stats[dim - 2, col] = _cstat(cs[1], cs[dim], _k, dim, nobs)
    p_value = 2 * np.vectorize(lambda z: pnorm(-abs(z)))(stats)
    return htest(
        statistic=stats,
        p_value=p_value,
        method="BDS Test",
        parameter={"m": list(range(2, m + 1)), "eps": [float(item) for item in eps]},
    )


_ADF_TABLE = -np.array(
    [
        [4.38, 3.95, 3.60, 3.24, 1.14, 0.80, 0.50, 0.15],
        [4.15, 3.80, 3.50, 3.18, 1.19, 0.87, 0.58, 0.24],
        [4.04, 3.73, 3.45, 3.15, 1.22, 0.90, 0.62, 0.28],
        [3.99, 3.69, 3.43, 3.13, 1.23, 0.92, 0.64, 0.31],
        [3.98, 3.68, 3.42, 3.13, 1.24, 0.93, 0.65, 0.32],
        [3.96, 3.66, 3.41, 3.12, 1.25, 0.94, 0.66, 0.33],
    ],
    dtype=float,
)
_ADF_N = [25, 50, 100, 250, 500, 100000]
_ADF_P = [0.01, 0.025, 0.05, 0.10, 0.90, 0.95, 0.975, 0.99]


def adf_test(x, alternative="stationary", k=None):
    series = _vector(x)
    if k is None:
        k = math.trunc((len(series) - 1) ** (1.0 / 3.0))
    k = int(k)
    if k < 0:
        raise ValueError("k negative")
    alternative = match_arg(alternative, ("stationary", "explosive"))
    k = k + 1
    changes = np.diff(series)
    n = len(changes)
    lagged = embed(changes, k)
    yt = lagged[:, 0]
    xt1 = series[k - 1 : n]
    tt = np.arange(k, n + 1, dtype=float)
    if k > 1:
        design = np.column_stack([ones(len(yt)), xt1, tt, lagged[:, 1:k]])
    else:
        design = np.column_stack([ones(len(yt)), xt1, tt])
    fit = lm(yt, design)
    stat = float(fit["coef"][1] / fit["se"][1])
    p_value = critical_p(_ADF_TABLE, _ADF_N, _ADF_P, stat, n)
    if alternative == "explosive":
        p_value = 1.0 - p_value
    return htest(
        statistic=stat,
        parameter=k - 1,
        alternative=alternative,
        p_value=p_value,
        method="Augmented Dickey-Fuller Test",
    )


def _type_arg(type):
    if str(type).lower().startswith("chisq") and type != "Chisq":
        warnings.warn(
            "value 'chisq' for 'type' is deprecated, use 'Chisq' instead",
            stacklevel=3,
        )
        return "Chisq"
    return match_arg(type, ("Chisq", "F"))


def _nn_stat(t_len, ssr0, ssr, kind, qstar, df2):
    if kind == "Chisq":
        stat = t_len * math.log(ssr0 / ssr)
        return stat, pchisq_sf(stat, qstar), qstar
    stat = ((ssr0 - ssr) / qstar) / (ssr / df2)
    return stat, pf_sf(stat, qstar, df2), (qstar, df2)


def white_test(x, y=None, lag=1, qstar=2, q=10, range=4, type="Chisq", scale=True):
    if y is None:
        return _white_ts(x, lag=lag, qstar=qstar, q=q, range=range, type=type, scale=scale)
    return _white_default(x, y, qstar=qstar, q=q, range=range, type=type, scale=scale)


def _runif_matrix(nrow, ncol, low, high):
    from boot.rng import unif

    draws = [low + (high - low) * unif() for _ in range(nrow * ncol)]
    return np.array(draws, dtype=float).reshape((nrow, ncol), order="F")


def _white_default(x, y, qstar, q, range, type, scale):
    kind = _type_arg(type)
    predictors = np.asarray(x, dtype=float)
    response = np.asarray(y, dtype=float)
    if predictors.ndim == 1:
        predictors = predictors.reshape(-1, 1)
    if response.ndim == 1:
        response = response.reshape(-1, 1)
    if np.isnan(predictors).any():
        raise ValueError("NAs in x")
    if np.isnan(response).any():
        raise ValueError("NAs in y")
    nin = predictors.shape[1]
    t_len = predictors.shape[0]
    if response.shape[0] != t_len:
        raise ValueError("number of rows of x and y must match")
    if response.shape[1] > 1:
        raise ValueError("handles only univariate outputs")
    if scale:
        predictors = r_scale(predictors)
        response = r_scale(response)
    design = np.column_stack([ones(t_len), predictors])
    fit = lm(response.reshape(-1), design)
    u = fit["resid"]
    ssr0 = float(np.dot(u, u))
    half = range / 2
    gamma = _runif_matrix(nin + 1, q, -half, half)
    raw = np.column_stack([ones(t_len), predictors])
    phantom = 1.0 / (1.0 + np.exp(-(raw @ gamma)))
    scores = prcomp_scores(phantom)[:, 1 : qstar + 1]
    design2 = np.column_stack([ones(t_len), predictors, scores])
    fit2 = lm(u, design2)
    ssr = float(np.dot(fit2["resid"], fit2["resid"]))
    stat, p_value, parameter = _nn_stat(t_len, ssr0, ssr, kind, qstar, t_len - qstar - nin)
    return htest(
        statistic=stat,
        parameter=parameter,
        p_value=p_value,
        method="White Neural Network Test",
    )


def _white_ts(x, lag, qstar, q, range, type, scale):
    kind = _type_arg(type)
    series = _vector(x)
    lag = int(lag)
    if lag < 1:
        raise ValueError("minimum lag is 1")
    t_len = len(series)
    if scale:
        series = r_scale(series)
    window = embed(series, lag + 1)
    design = np.column_stack([ones(len(window)), window[:, 1:]])
    fit = lm(window[:, 0], design)
    u = fit["resid"]
    ssr0 = float(np.dot(u, u))
    half = range / 2
    gamma = _runif_matrix(lag + 1, q, -half, half)
    raw = np.column_stack([ones(t_len - lag), window[:, 1:]])
    phantom = 1.0 / (1.0 + np.exp(-(raw @ gamma)))
    scores = prcomp_scores(phantom)[:, 1 : qstar + 1]
    design2 = np.column_stack([ones(len(u)), window[:, 1:], scores])
    fit2 = lm(u, design2)
    ssr = float(np.dot(fit2["resid"], fit2["resid"]))
    stat, p_value, parameter = _nn_stat(t_len, ssr0, ssr, kind, qstar, t_len - lag - qstar)
    return htest(
        statistic=stat,
        parameter=parameter,
        p_value=p_value,
        method="White Neural Network Test",
    )


def _products(columns, degree):
    width = columns.shape[1]
    pieces = []
    if degree == 2:
        for i in range(width):
            for j in range(i, width):
                pieces.append(columns[:, i] * columns[:, j])
    else:
        for i in range(width):
            for j in range(i, width):
                for k in range(j, width):
                    pieces.append(columns[:, i] * columns[:, j] * columns[:, k])
    if not pieces:
        return np.zeros((columns.shape[0], 0))
    return np.column_stack(pieces)


def terasvirta_test(x, y=None, lag=1, type="Chisq", scale=True):
    if y is None:
        return _terasvirta_ts(x, lag=lag, type=type, scale=scale)
    return _terasvirta_default(x, y, type=type, scale=scale)


def _terasvirta_default(x, y, type, scale):
    kind = _type_arg(type)
    predictors = np.asarray(x, dtype=float)
    response = np.asarray(y, dtype=float)
    if predictors.ndim == 1:
        predictors = predictors.reshape(-1, 1)
    if response.ndim == 1:
        response = response.reshape(-1, 1)
    if np.isnan(predictors).any():
        raise ValueError("NAs in x")
    if np.isnan(response).any():
        raise ValueError("NAs in y")
    nin = predictors.shape[1]
    t_len = predictors.shape[0]
    if response.shape[0] != t_len:
        raise ValueError("number of rows of x and y must match")
    if response.shape[1] > 1:
        raise ValueError("handles only univariate outputs")
    if scale:
        predictors = r_scale(predictors)
        response = r_scale(response)
    design = np.column_stack([ones(t_len), predictors])
    fit = lm(response.reshape(-1), design)
    u = fit["resid"]
    ssr0 = float(np.dot(u, u))
    extra = np.column_stack([_products(predictors, 2), _products(predictors, 3)])
    m = extra.shape[1]
    design2 = np.column_stack([ones(t_len), predictors, extra])
    fit2 = lm(u, design2)
    ssr = float(np.dot(fit2["resid"], fit2["resid"]))
    stat, p_value, parameter = _nn_stat(t_len, ssr0, ssr, kind, m, t_len - nin - m)
    return htest(
        statistic=stat,
        parameter=parameter,
        p_value=p_value,
        method="Teraesvirta Neural Network Test",
    )


def _terasvirta_ts(x, lag, type, scale):
    kind = _type_arg(type)
    series = _vector(x)
    lag = int(lag)
    if lag < 1:
        raise ValueError("minimum lag is 1")
    t_len = len(series)
    if scale:
        series = r_scale(series)
    window = embed(series, lag + 1)
    lagged = window[:, 1:]
    design = np.column_stack([ones(len(window)), lagged])
    fit = lm(window[:, 0], design)
    u = fit["resid"]
    ssr0 = float(np.dot(u, u))
    extra = np.column_stack([_products(lagged, 2), _products(lagged, 3)])
    m = extra.shape[1]
    design2 = np.column_stack([ones(len(u)), lagged, extra])
    fit2 = lm(u, design2)
    ssr = float(np.dot(fit2["resid"], fit2["resid"]))
    stat, p_value, parameter = _nn_stat(t_len, ssr0, ssr, kind, m, t_len - lag - m)
    return htest(
        statistic=stat,
        parameter=parameter,
        p_value=p_value,
        method="Teraesvirta Neural Network Test",
    )


def jarque_bera_test(x):
    series = _vector(x)
    n = len(series)
    m1 = float(series.sum() / n)
    centered = series - m1
    m2 = float(np.dot(centered, centered) / n)
    m3 = float(np.sum(centered**3) / n)
    m4 = float(np.sum(centered**4) / n)
    b1 = (m3 / m2 ** 1.5) ** 2
    b2 = m4 / m2**2
    stat = n * b1 / 6 + n * (b2 - 3) ** 2 / 24
    return htest(
        statistic=stat,
        parameter=2,
        p_value=pchisq_sf(stat, 2),
        method="Jarque Bera Test",
    )


_PP_Z_ALPHA = -np.array(
    [
        [22.5, 19.9, 17.9, 15.6, 3.66, 2.51, 1.53, 0.43],
        [25.7, 22.4, 19.8, 16.8, 3.71, 2.60, 1.66, 0.65],
        [27.4, 23.6, 20.7, 17.5, 3.74, 2.62, 1.73, 0.75],
        [28.4, 24.4, 21.3, 18.0, 3.75, 2.64, 1.78, 0.82],
        [28.9, 24.8, 21.5, 18.1, 3.76, 2.65, 1.78, 0.84],
        [29.5, 25.1, 21.8, 18.3, 3.77, 2.66, 1.79, 0.87],
    ],
    dtype=float,
)


def pp_test(x, alternative="stationary", type="Z(alpha)", lshort=True):
    series = _vector(x)
    kind = match_arg(type, ("Z(alpha)", "Z(t_alpha)"))
    alternative = match_arg(alternative, ("stationary", "explosive"))
    window = embed(series, 2)
    yt = window[:, 0]
    yt1 = window[:, 1]
    n = len(yt)
    tt = np.arange(1, n + 1, dtype=float) - n / 2
    fit = lm(yt, np.column_stack([ones(n), tt, yt1]))
    if fit["rank"] < 3:
        raise ValueError("Singularities in regression")
    u = fit["resid"]
    ssqru = float(np.dot(u, u) / n)
    if lshort:
        lag = math.trunc(4 * (n / 100) ** 0.25)
    else:
        lag = math.trunc(12 * (n / 100) ** 0.25)
    ssqrtl = pp_sum(u, lag, ssqru)
    n2 = n**2
    idx = np.arange(1, n + 1, dtype=float)
    trm1 = n2 * (n2 - 1) * np.sum(yt1**2) / 12
    trm2 = n * np.sum(yt1 * idx) ** 2
    trm3 = n * (n + 1) * np.sum(yt1 * idx) * np.sum(yt1)
    trm4 = (n * (n + 1) * (2 * n + 1) * np.sum(yt1) ** 2) / 6
    dx = trm1 - trm2 + trm3 - trm4
    if kind == "Z(alpha)":
        alpha = float(fit["coef"][2])
        stat = n * (alpha - 1) - (n**6) / (24 * dx) * (ssqrtl - ssqru)
        table = _PP_Z_ALPHA
    else:
        tstat = (float(fit["coef"][2]) - 1) / float(fit["se"][2])
        stat = math.sqrt(ssqru) / math.sqrt(ssqrtl) * tstat - (n**3) / (
            4 * math.sqrt(3) * math.sqrt(dx) * math.sqrt(ssqrtl)
        ) * (ssqrtl - ssqru)
        table = _ADF_TABLE
    p_value = critical_p(table, _ADF_N, _ADF_P, stat, n)
    if alternative == "explosive":
        p_value = 1.0 - p_value
    return htest(
        statistic=stat,
        parameter=lag,
        alternative=alternative,
        p_value=p_value,
        method="Phillips-Perron Unit Root Test",
    )


_PO_DEMEAN = -np.array(
    [
        [28.32, 23.81, 20.49, 18.48, 17.04, 15.93, 14.91],
        [34.17, 29.74, 26.09, 23.87, 22.19, 21.04, 19.95],
        [41.13, 35.71, 32.06, 29.51, 27.58, 26.23, 25.05],
        [47.51, 41.64, 37.15, 34.71, 32.74, 31.15, 29.88],
        [52.17, 46.53, 41.94, 39.11, 37.01, 35.48, 34.20],
    ],
    dtype=float,
)
_PO_STANDARD = -np.array(
    [
        [22.83, 18.89, 15.64, 13.81, 12.54, 11.57, 10.74],
        [29.27, 25.21, 21.48, 19.61, 18.18, 17.01, 16.02],
        [36.16, 31.54, 27.85, 25.52, 23.92, 22.62, 21.53],
        [42.87, 37.48, 33.48, 30.93, 28.85, 27.40, 26.17],
        [48.52, 42.55, 38.09, 35.51, 33.80, 32.27, 30.90],
    ],
    dtype=float,
)
_PO_P = [0.01, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15]


def po_test(x, demean=True, lshort=True):
    series = np.asarray(x, dtype=float)
    if series.ndim != 2 or series.shape[1] <= 1:
        raise ValueError("x is not a matrix or multivariate time series")
    dimx = series.shape[1]
    if dimx > 6:
        raise ValueError("no critical values for this dimension")
    if demean:
        design = np.column_stack([ones(series.shape[0]), series[:, 1:]])
    else:
        design = series[:, 1:]
    fit = lm(series[:, 0], design)
    window = embed(fit["resid"], 2)
    ut = window[:, 0]
    ut1 = window[:, 1]
    n = len(ut)
    second = lm(ut, ut1)
    if second["rank"] < 1:
        raise ValueError("Singularities in regression")
    k = second["resid"]
    ssqrk = float(np.dot(k, k) / n)
    if lshort:
        lag = math.trunc(n / 100)
    else:
        lag = math.trunc(n / 30)
    ssqrtl = pp_sum(k, lag, ssqrk)
    alpha = float(second["coef"][0])
    stat = n * (alpha - 1) - 0.5 * n**2 * (ssqrtl - ssqrk) / np.sum(ut1**2)
    table = _PO_DEMEAN if demean else _PO_STANDARD
    row = table[dimx - 2]
    p_value = approx(row, _PO_P, stat, rule=2)
    if math.isnan(approx(row, _PO_P, stat, rule=1)):
        if p_value == min(_PO_P):
            warnings.warn("p-value smaller than printed p-value", stacklevel=2)
        else:
            warnings.warn("p-value greater than printed p-value", stacklevel=2)
    return htest(
        statistic=float(stat),
        parameter=lag,
        p_value=p_value,
        method="Phillips-Ouliaris Cointegration Test",
    )


def kpss_test(x, null="Level", lshort=True):
    series = _vector(x)
    null = match_arg(null, ("Level", "Trend"))
    n = len(series)
    if null == "Trend":
        tt = np.arange(1, n + 1, dtype=float)
        fit = lm(series, np.column_stack([ones(n), tt]))
        table = np.array([0.216, 0.176, 0.146, 0.119])
    else:
        fit = lm(series, ones(n))
        table = np.array([0.739, 0.574, 0.463, 0.347])
    fitted = fit["fitted"]
    resvar = fit["sigma2"]
    spread = float(np.mean(fitted) ** 2 + np.var(fitted, ddof=1))
    if math.isfinite(resvar) and resvar < spread * 1e-30:
        warnings.warn("essentially perfect fit: test may be unreliable", stacklevel=2)
    e = fit["resid"]
    tablep = [0.01, 0.025, 0.05, 0.10]
    partial = np.cumsum(e)
    eta = float(np.dot(partial, partial) / n**2)
    s2 = float(np.dot(e, e) / n)
    if lshort:
        lag = math.trunc(4 * (n / 100) ** 0.25)
    else:
        lag = math.trunc(12 * (n / 100) ** 0.25)
    s2 = pp_sum(e, lag, s2)
    stat = eta / s2
    p_value = approx(table, tablep, stat, rule=2)
    if not math.isnan(stat) and math.isnan(approx(table, tablep, stat, rule=1)):
        if p_value == min(tablep):
            warnings.warn("p-value smaller than printed p-value", stacklevel=2)
        else:
            warnings.warn("p-value greater than printed p-value", stacklevel=2)
    return htest(
        statistic=stat,
        parameter=lag,
        p_value=p_value,
        method=f"KPSS Test for {null} Stationarity",
    )
