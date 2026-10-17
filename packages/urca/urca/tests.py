"""Augmented Dickey-Fuller, KPSS, and Phillips-Perron tests.

The statistics are the t ratios and nested-model F ratios from the same
regressions as the R functions. Critical values are the tables in those functions.
"""

from __future__ import annotations

import math

import numpy as np

_PCT = ("1pct", "5pct", "10pct")
_KPSS_PCT = ("10pct", "5pct", "2.5pct", "1pct")


class UnitRoot:
    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __str__(self):
        stats = " ".join(f"{value:.6g}" for value in self.teststat)
        return f"{self.test_name}: {stats}"


def ur_df(y, type="none", lags=1, selectlags="Fixed"):
    """Augmented Dickey-Fuller test. type is none, drift, or trend."""
    kind = _match(type, ("none", "drift", "trend"))
    select = _match(selectlags, ("Fixed", "AIC", "BIC"))
    array = np.asarray(y, dtype=float)
    if array.ndim == 2 and array.shape[1] > 1:
        raise ValueError("\ny is not a vector or univariate time series.\n")
    series = [float(value) for value in array.ravel()]
    if any(math.isnan(value) for value in series):
        raise ValueError("\nNAs in y.\n")
    lag = int(lags)
    if lag < 0:
        raise ValueError("\nLags must be set to an non negative integer value.\n")
    changes = _diff(series)
    n = len(changes)
    order = lag + 1
    embedded = _embed(changes, order)
    z_diff = [row[0] for row in embedded]
    z_lag = series[order - 1 : n]
    trend = list(range(order, n + 1))
    if order > 1 and select != "Fixed":
        scores = [math.nan] * order
        penalty = 2.0 if select == "AIC" else math.log(len(z_diff))
        for i in range(2, order + 1):
            extra = [row[1:i] for row in embedded]
            design, _names = _adf_design(kind, z_lag, trend, extra)
            fit = _ols(z_diff, design)
            scores[i - 1] = _aic(fit, penalty)
        order = scores.index(min(score for score in scores if not math.isnan(score))) + 1
    extra = [row[1:order] for row in embedded] if order > 1 else None
    design, names = _adf_design(kind, z_lag, trend, extra)
    fit = _ols(z_diff, design)
    formula, coef_names = _adf_formula(kind, max(order - 1, 0))
    testreg = {"formula": formula, "coef_names": coef_names, "fit": fit, "response": np.asarray(z_diff, dtype=float)}
    if kind == "none":
        teststat = [fit["t"][0]]
        testnames = ["tau1"]
    elif kind == "drift":
        reduced = _ols(z_diff, _columns(extra) if extra is not None else np.zeros((len(z_diff), 0)))
        phi = _anova_f(reduced, fit)
        teststat = [fit["t"][1], phi]
        testnames = ["tau2", "phi1"]
    else:
        lag_only = _columns(extra) if extra is not None else np.zeros((len(z_diff), 0))
        phi2 = _anova_f(_ols(z_diff, lag_only), fit)
        phi3 = _anova_f(_ols(z_diff, _with_intercept(lag_only)), fit)
        teststat = [fit["t"][1], phi2, phi3]
        testnames = ["tau3", "phi2", "phi3"]
    return UnitRoot(
        y=series,
        model=kind,
        cval=_adf_critical(kind, n),
        cval_names=testnames,
        lags=lag,
        teststat=teststat,
        test_names=testnames,
        residuals=fit["residuals"],
        res=fit["residuals"],
        testreg=testreg,
        test_name="Augmented Dickey-Fuller Test",
    )


def ur_kpss(y, type="mu", lags="short", use_lag=None):
    """KPSS stationarity test. type is mu or tau."""
    kind = _match(type, ("mu", "tau"))
    lag_name = _match(lags, ("short", "long", "nil"))
    series = _drop_missing(y)
    n = len(series)
    if use_lag is not None:
        lmax = int(use_lag)
        if lmax < 0:
            lmax = math.trunc(4 * (n / 100) ** 0.25)
    elif lag_name == "short":
        lmax = math.trunc(4 * (n / 100) ** 0.25)
    elif lag_name == "long":
        lmax = math.trunc(12 * (n / 100) ** 0.25)
    else:
        lmax = 0
    if kind == "mu":
        critical = [0.347, 0.463, 0.574, 0.739]
        center = float(np.mean(series))
        residuals = [value - center for value in series]
    else:
        critical = [0.119, 0.146, 0.176, 0.216]
        trend = np.column_stack((np.ones(n), np.arange(1, n + 1)))
        residuals = _ols(series, trend)["residuals"]
    partial = np.cumsum(residuals)
    numerator = float(np.dot(partial, partial)) / n**2
    s2 = float(np.dot(residuals, residuals)) / n
    if lmax == 0:
        denominator = s2
    else:
        covariance = [_lag_product(residuals, lag) for lag in range(1, lmax + 1)]
        bartlett = [1 - lag / (lmax + 1) for lag in range(1, lmax + 1)]
        denominator = s2 + 2 / n * float(np.dot(bartlett, covariance))
    return UnitRoot(
        y=series,
        type=kind,
        lag=lmax,
        teststat=[numerator / denominator],
        cval=[critical],
        cval_names=["critical values"],
        residuals=residuals,
        res=residuals,
        test_name="KPSS",
        _pct=_KPSS_PCT,
    )


def ur_pp(x, type="Z-alpha", model="constant", lags="short", use_lag=None):
    """Phillips-Perron test. model is constant or trend."""
    kind = _match(type, ("Z-alpha", "Z-tau"))
    spec = _match(model, ("constant", "trend"))
    lag_name = _match(lags, ("short", "long"))
    series = _drop_missing(x)
    level = series[:-1]
    change = series[1:]
    n = len(change)
    if use_lag is not None:
        lmax = int(use_lag)
        if lmax < 0:
            lmax = math.trunc(4 * (n / 100) ** 0.25)
    elif lag_name == "short":
        lmax = math.trunc(4 * (n / 100) ** 0.25)
    else:
        lmax = math.trunc(12 * (n / 100) ** 0.25)
    if spec == "trend":
        critical = [
            -3.9638 - 8.353 / n - 47.44 / n**2,
            -3.4126 - 4.039 / n - 17.83 / n**2,
            -3.1279 - 2.418 / n - 7.58 / n**2,
        ]
        label = "with intercept and trend"
        trend = np.arange(1, n + 1) - n / 2
        design = np.column_stack((np.ones(n), level, trend))
        fit = _ols(change, design)
        residuals = fit["residuals"]
        s = float(np.dot(residuals, residuals)) / n
        myybar = float(np.dot(change - np.mean(change), change - np.mean(change))) / n**2
        myy = float(np.dot(change, change)) / n**2
        times = np.arange(1, n + 1)
        mty = float(np.dot(times, change)) / n**2.5
        my = float(np.sum(change)) / n**1.5
        sig = _long_run(residuals, s, n, lmax)
        lam = 0.5 * (sig - s)
        lam_p = lam / sig
        moment = (1 - n ** -2) * myy - 12 * mty**2 + 12 * (1 + 1 / n) * mty * my - (4 + 6 / n + 2 / n**2) * my**2
        alpha = fit["coef"][1]
        alpha_se = fit["se"][1]
        if kind == "Z-tau":
            tstat = (alpha - 1) / alpha_se
            statistic = math.sqrt(s / sig) * tstat - lam_p * math.sqrt(sig) / math.sqrt(moment)
        else:
            statistic = n * (alpha - 1) - lam / moment
            critical = [math.nan, math.nan, math.nan]
    else:
        critical = [
            -3.4335 - 5.999 / n - 29.25 / n**2,
            -2.8621 - 2.738 / n - 8.36 / n**2,
            -2.5671 - 1.438 / n - 4.48 / n**2,
        ]
        label = "with intercept"
        design = np.column_stack((np.ones(n), level))
        fit = _ols(change, design)
        residuals = fit["residuals"]
        s = float(np.dot(residuals, residuals)) / n
        myybar = float(np.dot(change - np.mean(change), change - np.mean(change))) / n**2
        myy = float(np.dot(change, change)) / n**2
        sig = _long_run(residuals, s, n, lmax)
        lam = 0.5 * (sig - s)
        lam_p = lam / sig
        alpha = fit["coef"][1]
        alpha_se = fit["se"][1]
        if kind == "Z-tau":
            tstat = (alpha - 1) / alpha_se
            statistic = math.sqrt(s / sig) * tstat - lam_p * math.sqrt(sig) / math.sqrt(myybar)
        else:
            statistic = n * (alpha - 1) - lam / myybar
            critical = [math.nan, math.nan, math.nan]
    return UnitRoot(
        y=series[1:],
        type=kind,
        model=label,
        lag=lmax,
        teststat=[statistic],
        cval=[critical],
        residuals=residuals,
        res=residuals,
        test_name="Phillips-Perron",
    )


def _adf_formula(kind, lag_count):
    if lag_count == 1:
        lag_part = " + z.diff.lag"
    elif lag_count > 1:
        lag_part = " + " + " + ".join(["z.diff.lag"] * lag_count)
    else:
        lag_part = ""
    lag_names = ["z.diff.lag"] * lag_count
    if kind == "none":
        return f"z.diff ~ z.lag.1 - 1{lag_part}", ["z.lag.1", *lag_names]
    if kind == "drift":
        return f"z.diff ~ z.lag.1 + 1{lag_part}", ["(Intercept)", "z.lag.1", *lag_names]
    return f"z.diff ~ z.lag.1 + 1 + tt{lag_part}", ["(Intercept)", "z.lag.1", "tt", *lag_names]


def _adf_design(kind, z_lag, trend, extra):
    columns = []
    if kind != "none":
        columns.append(np.ones(len(z_lag)))
    columns.append(np.asarray(z_lag, dtype=float))
    if kind == "trend":
        columns.append(np.asarray(trend, dtype=float))
    if extra is not None:
        extra_columns = _columns(extra)
        for index in range(extra_columns.shape[1]):
            columns.append(extra_columns[:, index])
    return np.column_stack(columns), None


def _adf_critical(kind, n):
    if n < 25:
        row = 0
    elif n < 50:
        row = 1
    elif n < 100:
        row = 2
    elif n < 250:
        row = 3
    elif n < 500:
        row = 4
    else:
        row = 5
    tau1 = [
        [-2.66, -1.95, -1.60],
        [-2.62, -1.95, -1.61],
        [-2.60, -1.95, -1.61],
        [-2.58, -1.95, -1.62],
        [-2.58, -1.95, -1.62],
        [-2.58, -1.95, -1.62],
    ]
    tau2 = [
        [-3.75, -3.00, -2.63],
        [-3.58, -2.93, -2.60],
        [-3.51, -2.89, -2.58],
        [-3.46, -2.88, -2.57],
        [-3.44, -2.87, -2.57],
        [-3.43, -2.86, -2.57],
    ]
    phi1 = [
        [7.88, 5.18, 4.12],
        [7.06, 4.86, 3.94],
        [6.70, 4.71, 3.86],
        [6.52, 4.63, 3.81],
        [6.47, 4.61, 3.79],
        [6.43, 4.59, 3.78],
    ]
    tau3 = [
        [-4.38, -3.60, -3.24],
        [-4.15, -3.50, -3.18],
        [-4.04, -3.45, -3.15],
        [-3.99, -3.43, -3.13],
        [-3.98, -3.42, -3.13],
        [-3.96, -3.41, -3.12],
    ]
    phi2 = [
        [8.21, 5.68, 4.67],
        [7.02, 5.13, 4.31],
        [6.50, 4.88, 4.16],
        [6.22, 4.75, 4.07],
        [6.15, 4.71, 4.05],
        [6.09, 4.68, 4.03],
    ]
    phi3 = [
        [10.61, 7.24, 5.91],
        [9.31, 6.73, 5.61],
        [8.73, 6.49, 5.47],
        [8.43, 6.49, 5.47],
        [8.34, 6.30, 5.36],
        [8.27, 6.25, 5.34],
    ]
    if kind == "none":
        return [tau1[row]]
    if kind == "drift":
        return [tau2[row], phi1[row]]
    return [tau3[row], phi2[row], phi3[row]]


def _ols(y, design):
    """Least squares with an intercept already included in the design."""
    response = np.asarray(y, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    n, p = design.shape
    if p == 0:
        residuals = response.copy()
        return {
            "coef": np.array([]),
            "se": np.array([]),
            "t": np.array([]),
            "residuals": residuals,
            "rss": float(np.dot(residuals, residuals)),
            "df": n,
        }
    factor, triangular = np.linalg.qr(design, mode="reduced")
    coef = np.linalg.solve(triangular, factor.T @ response)
    residuals = response - design @ coef
    df = n - p
    sigma2 = float(np.dot(residuals, residuals)) / df
    gram = triangular.T @ triangular
    try:
        inverse = np.linalg.inv(gram)
    except np.linalg.LinAlgError:
        inverse = np.linalg.pinv(gram)
    se = np.sqrt(np.diag(inverse) * sigma2)
    return {
        "coef": coef,
        "se": se,
        "t": coef / se,
        "residuals": residuals,
        "rss": float(np.dot(residuals, residuals)),
        "df": df,
    }


def _anova_f(small, big):
    difference = small["df"] - big["df"]
    return ((small["rss"] - big["rss"]) / difference) / (big["rss"] / big["df"])


def _aic(fit, penalty):
    n = len(fit["residuals"])
    p = n - fit["df"]
    loglik = -n / 2 * (math.log(2 * math.pi) + math.log(fit["rss"] / n) + 1)
    return -2 * loglik + penalty * (p + 1)


def _columns(rows):
    return np.asarray(rows, dtype=float)


def _with_intercept(design):
    if design.size == 0:
        return np.ones((len(design), 1))
    return np.column_stack((np.ones(design.shape[0]), design))


def _long_run(residuals, s, n, lmax):
    if lmax <= 0:
        return s
    products = [_lag_product(residuals, lag) for lag in range(1, lmax + 1)]
    weights = [1 - lag / (lmax + 1) for lag in range(1, lmax + 1)]
    return s + (2 / n) * float(np.dot(weights, products))


def _lag_product(residuals, lag):
    values = np.asarray(residuals, dtype=float)
    return float(np.dot(values[lag:], values[:-lag]))


def _diff(values):
    return [values[index] - values[index - 1] for index in range(1, len(values))]


def _embed(values, lags):
    rows = []
    for start in range(0, len(values) - lags + 1):
        rows.append([values[start + lags - 1 - offset] for offset in range(lags)])
    return rows


def _drop_missing(values):
    kept = []
    for value in np.ravel(values):
        if value is None:
            continue
        number = float(value)
        if math.isnan(number):
            continue
        kept.append(number)
    return kept


def _match(value, choices):
    if value is None:
        return choices[0]
    hits = [choice for choice in choices if choice.startswith(value)]
    if len(hits) != 1:
        listed = ", ".join(f"“{choice}”" for choice in choices)
        raise ValueError(f"'arg' should be one of {listed}")
    return hits[0]
