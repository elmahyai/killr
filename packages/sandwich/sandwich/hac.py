"""Kernel HAC estimators, Newey-West, Andrews bandwidths, and WEAVE."""

from __future__ import annotations

import math
import warnings

import numpy as np

from .estfun import estfun, sandwich
from .model import Fit, Formula, SandwichError, match_arg, r_seq
from .series import Zoo, coredata, is_zoo

_KERNELS = ["Truncated", "Bartlett", "Parzen", "Tukey-Hanning", "Quadratic Spectral"]


def kweights(x, kernel="Truncated", normalize: bool = False) -> np.ndarray:
    kernel = match_arg(kernel, ["Truncated", "Bartlett", "Parzen", "Tukey-Hanning", "Quadratic Spectral"])
    values = np.asarray(x, dtype=float)
    scale = {"Truncated": 2, "Bartlett": 2 / 3, "Parzen": 0.539285, "Tukey-Hanning": 3 / 4, "Quadratic Spectral": 1}[kernel] if normalize else 1.0
    z = scale * values
    absolute = np.abs(z)
    if kernel == "Truncated":
        return np.where(absolute > 1, 0.0, 1.0)
    if kernel == "Bartlett":
        return np.where(absolute > 1, 0.0, 1 - absolute)
    if kernel == "Parzen":
        left = 1 - 6 * z ** 2 + 6 * absolute ** 3
        right = 2 * (1 - absolute) ** 3
        return np.where(absolute > 1, 0.0, np.where(absolute < 0.5, left, right))
    if kernel == "Tukey-Hanning":
        return np.where(absolute > 1, 0.0, (1 + np.cos(math.pi * z)) / 2)

    def qs(point):
        y = 6 * math.pi * point / 5
        return 3 * (1 / y) ** 2 * (math.sin(y) / y - math.cos(y))

    out = np.empty(values.shape, dtype=float)
    close = np.abs(values) < 1e-3
    if np.any(~close):
        out[~close] = np.vectorize(qs)(values[~close])
    if np.any(close):
        cf = 1e6 * math.log(qs(1e-3))
        out[close] = np.exp(cf * values[close] ** 2)
    return out


def _embed(x: np.ndarray, dimension: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        n = len(x)
        rows = n - dimension + 1
        return np.column_stack([x[(dimension - 1 - j):(dimension - 1 - j + rows)] for j in range(dimension)])
    nser = x.shape[1]
    out = np.zeros((x.shape[0] - dimension + 1, dimension * nser))
    for i in range(nser):
        out[:, i::nser] = _embed(x[:, i], dimension)
    return out


def ar_ols(x, order_max: int, demean: bool = False, aic: bool = False, intercept: bool | None = None) -> dict:
    """Unconstrained least-squares autoregression, matching ``stats::ar`` method ``ols``."""
    if intercept is None:
        intercept = demean
    series = np.asarray(x, dtype=float)
    if series.ndim == 1:
        series = series.reshape(-1, 1)
    n_used, nser = series.shape
    scale = np.sqrt(np.var(series, axis=0, ddof=1))
    scale[scale == 0] = 1
    scaled = series / scale
    order_max = int(round(order_max))
    centered = scaled - scaled.mean(axis=0) if demean else scaled
    m = order_max
    y = _embed(centered, m + 1)
    current = y[:, :nser]
    lags = y[:, nser:]
    if intercept:
        lags = np.column_stack([np.ones(lags.shape[0]), lags])
    gram = lags.T @ lags
    projection = np.linalg.inv(gram)
    coefficients = current.T @ lags @ projection
    if intercept:
        coefficients = coefficients[:, 1:]
    fitted = (np.column_stack([np.ones(y.shape[0]), y[:, nser:]]) if intercept else y[:, nser:])
    # Recompute with the same design the coefficients belong to.
    design = np.column_stack([np.ones(y.shape[0]), y[:, nser:]]) if intercept else y[:, nser:]
    full = current.T @ design @ np.linalg.inv(design.T @ design)
    fitted = full @ design.T
    error = current.T - fitted
    count = error.shape[1]
    variance = (error @ error.T) / count
    ar = np.transpose(np.ravel(coefficients, order="F").reshape((nser, nser, m), order="F"), (2, 0, 1))
    if nser > 1:
        for lag in range(m):
            ar[lag] = ar[lag] * np.outer(scale, 1 / scale)
        variance = variance * np.outer(scale, scale)
    residuals = np.vstack([np.full((m, nser), np.nan), error.T]) * scale
    return {"order": m, "ar": ar, "var.pred": variance if nser > 1 else float(variance * scale[0] ** 2), "resid": residuals}


def _order_index(n: int, order_by, data, fit: Fit | None) -> np.ndarray:
    if order_by is None:
        return np.arange(n)
    if isinstance(order_by, Formula):
        name = order_by.text.split("~", 1)[-1].strip()
        source = data if data is not None else fit.data
        values = np.asarray(source[name], dtype=float)
        if fit is not None and len(values) != n:
            values = values[fit.kept]
        return np.argsort(values, kind="mergesort")
    values = np.asarray(order_by, dtype=float).ravel()
    if fit is not None and len(values) != n and fit.na_action is not None:
        values = values[fit.kept]
    return np.argsort(values, kind="mergesort")


def _scores(x, order_by=None, data=None) -> np.ndarray:
    if isinstance(x, np.ndarray):
        values = np.asarray(coredata(x) if is_zoo(x) else x, dtype=float)
    else:
        values = estfun(x)
        if is_zoo(values):
            values = np.asarray(values.data, dtype=float)
        values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        values = values.reshape(-1, 1)
    index = _order_index(values.shape[0], order_by, data, x if isinstance(x, Fit) else None)
    return values[index]


def _column_weights(x, values: np.ndarray) -> np.ndarray:
    k = values.shape[1]
    weights = np.ones(k)
    names = getattr(x, "coef_names", None) if isinstance(x, Fit) else None
    if names and "(Intercept)" in names:
        weights[names.index("(Intercept)")] = 0
    elif isinstance(x, Fit):
        with np.errstate(divide="ignore", invalid="ignore"):
            residuals = np.nanmean(values / x.x, axis=1)
        close = np.sum((values - residuals[:, None]) ** 2, axis=0) < 1e-16
        weights[close] = 0
    if np.all(weights <= 0):
        weights[:] = 1
    if len(weights) < 2:
        return np.array([1.0])
    return weights


def meatHAC(x, order_by=None, prewhite=False, weights=None, adjust: bool = True, diagnostics: bool = False, ar_method: str = "ols", data=None, **_kwargs) -> np.ndarray:
    if weights is None:
        weights = weightsAndrews
    prewhite = int(prewhite)
    values = _scores(x, order_by, data)
    n_orig, k = values.shape
    if prewhite > 0:
        fitted = ar_ols(values, prewhite, demean=False, aic=False)
        if k > 1:
            summed = fitted["ar"].sum(axis=0)
            transform = np.linalg.inv(np.eye(k) - summed)
        else:
            transform = np.array([[1.0 / (1.0 - float(np.sum(fitted["ar"])))]])
        values = np.asarray(fitted["resid"], dtype=float)
        values = values[~np.isnan(values).any(axis=1)]
    else:
        transform = None
    n = values.shape[0]
    if callable(weights):
        weights = weights(x, order_by=order_by, prewhite=prewhite, ar_method=ar_method, data=data)
    weights = np.asarray(weights, dtype=float).ravel()
    if len(weights) > n:
        warnings.warn("more weights than observations, only first n used", RuntimeWarning, stacklevel=2)
        weights = weights[:n]
    total = 0.5 * (values.T @ values) * weights[0]
    if len(weights) > 1:
        for lag, weight in enumerate(weights[1:], start=2):
            total = total + weight * (values[: n - lag + 1].T @ values[lag - 1 :])
    total = total + total.T
    if adjust:
        total = n_orig / (n_orig - k) * total
    if prewhite > 0:
        total = transform @ total @ transform.T
    result = total / n_orig
    if diagnostics:
        result = result.copy()
    return result


def bwAndrews(x, order_by=None, kernel="Quadratic Spectral", approx="AR(1)", weights=None, prewhite=1, ar_method="ols", data=None, **_kwargs) -> float:
    kernel = match_arg(kernel, ["Quadratic Spectral", "Truncated", "Bartlett", "Parzen", "Tukey-Hanning"])
    approx = match_arg(approx, ["AR(1)", "ARMA(1,1)"])
    prewhite = int(prewhite)
    values = _scores(x, order_by, data)
    n, k = values.shape
    if weights is None:
        weights = _column_weights(x, values)
    else:
        weights = np.resize(np.asarray(weights, dtype=float), k)
    if prewhite > 0:
        fitted = ar_ols(values, prewhite, demean=False, aic=False)
        values = np.asarray(fitted["resid"], dtype=float)
        values = values[~np.isnan(values).any(axis=1)]
        n = values.shape[0]
    if approx != "AR(1)":
        raise SandwichError("ARMA(1,1) bandwidth uses arima, which is not available without a new native library")
    rho = []
    sigma = []
    for column in range(values.shape[1]):
        try:
            fitted = ar_ols(values[:, column], 1, demean=True, aic=False)
            # ar.ols demean=TRUE is the default of ar(); bwAndrews calls ar(..., method="ols") which demeans.
            coefficient = float(np.sum(fitted["ar"]))
            variance = float(fitted["var.pred"])
            rho.append(coefficient)
            sigma.append(math.sqrt(variance) if variance >= 0 else float("nan"))
        except np.linalg.LinAlgError:
            rho.append(float("nan"))
            sigma.append(float("nan"))
    rho = np.array(rho)
    sigma = np.array(sigma)
    if not np.all(np.isfinite(rho) * np.isfinite(sigma)):
        raise SandwichError("Cannot compute bandwidth because AR(1) approximation failed")
    denum = np.sum(weights * (sigma / (1 - rho)) ** 4)
    alpha2 = np.sum(weights * 4 * rho ** 2 * sigma ** 4 / (1 - rho) ** 8) / denum
    alpha1 = np.sum(weights * 4 * rho ** 2 * sigma ** 4 / ((1 - rho) ** 6 * (1 + rho) ** 2)) / denum
    if kernel == "Truncated":
        return 0.6611 * (n * alpha2) ** 0.2
    if kernel == "Bartlett":
        return 1.1447 * (n * alpha1) ** (1 / 3)
    if kernel == "Parzen":
        return 2.6614 * (n * alpha2) ** 0.2
    if kernel == "Tukey-Hanning":
        return 1.7462 * (n * alpha2) ** 0.2
    return 1.3221 * (n * alpha2) ** 0.2


def weightsAndrews(x, order_by=None, bw=None, kernel="Quadratic Spectral", prewhite=1, ar_method="ols", tol=1e-7, data=None, verbose: bool = False, **kwargs) -> np.ndarray:
    kernel = match_arg(kernel, ["Quadratic Spectral", "Truncated", "Bartlett", "Parzen", "Tukey-Hanning"])
    if bw is None:
        bw = bwAndrews
    if callable(bw):
        bw = bw(x, order_by=order_by, kernel=kernel, prewhite=prewhite, data=data, ar_method=ar_method, **kwargs)
    n = _scores(x, order_by, data).shape[0] - int(prewhite)
    weights = kweights(np.arange(n) / bw, kernel=kernel)
    last = int(np.max(np.flatnonzero(np.abs(weights) > tol)))
    return weights[: last + 1]


def vcovHAC(x, order_by=None, prewhite=False, weights=None, adjust: bool = True, diagnostics: bool = False, sandwich_=True, ar_method="ols", data=None, **kwargs) -> np.ndarray:
    if x.klass[0] == "mlm" and False:
        pass
    meat = meatHAC(x, order_by=order_by, prewhite=prewhite, weights=weights, adjust=adjust, diagnostics=diagnostics, ar_method=ar_method, data=data)
    if sandwich_:
        return sandwich(x, meat_=meat, **kwargs)
    return meat


vcovHAC_default = vcovHAC


def kernHAC(x, order_by=None, prewhite=1, bw=None, kernel="Quadratic Spectral", approx="AR(1)", adjust: bool = True, diagnostics: bool = False, sandwich_=True, ar_method="ols", tol=1e-7, data=None, verbose: bool = False, **kwargs) -> np.ndarray:
    if bw is None:
        bw = bwAndrews

    def myweights(x, order_by=None, prewhite=False, ar_method="ols", data=None, **_ignored):
        return weightsAndrews(x, order_by=order_by, prewhite=prewhite, bw=bw, kernel=kernel, approx=approx, ar_method=ar_method, tol=tol, data=data, verbose=verbose)

    return vcovHAC(x, order_by=order_by, prewhite=prewhite, weights=myweights, adjust=adjust, diagnostics=diagnostics, sandwich_=sandwich_, ar_method=ar_method, data=data)


def bwNeweyWest(x, order_by=None, kernel="Bartlett", weights=None, prewhite=1, ar_method="ols", data=None, **_kwargs) -> float:
    kernel = match_arg(kernel, ["Bartlett", "Parzen", "Quadratic Spectral", "Truncated", "Tukey-Hanning"])
    if kernel in {"Truncated", "Tukey-Hanning"}:
        raise SandwichError("Automatic bandwidth selection only available for Bartlett, Parzen and Quadratic Spectral kernels. Use bwAndrews instead.")
    prewhite = int(prewhite)
    values = _scores(x, order_by, data)
    n, k = values.shape
    if weights is None:
        weights = _column_weights(x, values)
    else:
        weights = np.resize(np.asarray(weights, dtype=float), k)
    rate = {"Bartlett": 2 / 9, "Parzen": 4 / 25, "Quadratic Spectral": 2 / 25}[kernel]
    m = int(math.floor((3 if prewhite > 0 else 4) * (n / 100) ** rate))
    if prewhite > 0:
        fitted = ar_ols(values, prewhite, demean=False, aic=False)
        values = np.asarray(fitted["resid"], dtype=float)
        values = values[~np.isnan(values).any(axis=1)]
        n = values.shape[0]
    hw = values @ weights
    sigma = np.array([np.sum(hw[: n - j] * hw[j:]) / n for j in range(m + 1)])
    s0 = sigma[0] + 2 * np.sum(sigma[1:])
    s1 = 2 * np.sum(np.arange(1, m + 1) * sigma[1:])
    s2 = 2 * np.sum(np.arange(1, m + 1) ** 2 * sigma[1:])
    qrate = 1 / (2 * (1 if kernel == "Bartlett" else 2) + 1)
    if kernel == "Bartlett":
        rval = 1.1447 * ((s1 / s0) ** 2) ** qrate
    elif kernel == "Parzen":
        rval = 2.6614 * ((s2 / s0) ** 2) ** qrate
    else:
        rval = 1.3221 * ((s2 / s0) ** 2) ** qrate
    return float(rval * (n + prewhite) ** qrate)


def NeweyWest(x, lag=None, order_by=None, prewhite=True, adjust: bool = False, diagnostics: bool = False, sandwich_=True, ar_method="ols", data=None, verbose: bool = False) -> np.ndarray:
    if lag is None:
        lag = math.floor(bwNeweyWest(x, order_by=order_by, prewhite=prewhite, ar_method=ar_method, data=data))
    weights = r_seq(1, 0, -1 / (lag + 1))
    return vcovHAC(x, order_by=order_by, prewhite=prewhite, weights=weights, adjust=adjust, diagnostics=diagnostics, sandwich_=sandwich_, ar_method=ar_method, data=data)


def pava_blocks(x, w=None, b=None, up: bool = True) -> dict:
    x = np.asarray(x, dtype=float).copy()
    w = np.ones(len(x)) if w is None else np.asarray(w, dtype=float).copy()
    b = np.ones(len(x)) if b is None else np.asarray(b, dtype=float).copy()
    if len(x) == 1:
        return {"x": x, "blocks": b, "increasing": up}
    last = 0
    for i in range(1, len(x)):
        if x[i] <= x[last] and up:
            total = w[last] + w[i]
            x[last] = (x[last] * w[last] + x[i] * w[i]) / total
            w[last] = total
            b[last] = b[i] + b[last]
            b[i] = 0
        elif x[i] <= x[last] and not up:
            last = i
        elif x[i] > x[last] and not up:
            total = w[last] + w[i]
            x[last] = (x[last] * w[last] + x[i] * w[i]) / total
            w[last] = total
            b[last] = b[i] + b[last]
            b[i] = 0
        elif x[i] > x[last] and up:
            last = i
    if np.any(b == 0):
        keep = b > 0
        return pava_blocks(x[keep], w[keep], b[keep], up)
    return {"x": x, "blocks": b, "increasing": up}


def _isoreg(y: np.ndarray) -> np.ndarray:
    y = [float(item) for item in y]
    values: list[float] = []
    weights: list[float] = []
    lengths: list[int] = []
    for item in y:
        values.append(item)
        weights.append(1.0)
        lengths.append(1)
        while len(values) >= 2 and values[-2] > values[-1]:
            weight = weights.pop()
            value = values.pop()
            length = lengths.pop()
            weights[-1] += weight
            lengths[-1] += length
            values[-1] = (values[-1] * (weights[-1] - weight) + value * weight) / weights[-1]
    out = []
    for value, length in zip(values, lengths):
        out.extend([value] * length)
    return np.array(out)


def _acf(x: np.ndarray, lag_max: int) -> np.ndarray:
    centered = x - np.mean(x)
    n = len(centered)
    scale = np.dot(centered, centered) / n
    lags = [1.0]
    for lag in range(1, lag_max + 1):
        lags.append(float(np.dot(centered[: n - lag], centered[lag:]) / n / scale))
    return np.array(lags)


def _acf_weave(x: np.ndarray, lag: int) -> np.ndarray:
    centered = x - np.mean(x)
    covs = []
    for ii in range(2, lag + 1):
        left = centered[: len(centered) - ii + 1]
        right = centered[ii - 1 :]
        covs.append(float(np.cov(left, right, ddof=1)[0, 1]))
    return np.array(covs) / np.var(centered, ddof=1)


def isoacf(x, lagmax=None, weave1: bool = False) -> np.ndarray:
    values = np.asarray(coredata(x) if is_zoo(x) else x, dtype=float).ravel()
    if weave1:
        lagmax = min(len(values) - 1, int(math.trunc(5 * math.sqrt(len(values)))))
        covs = _acf_weave(values, lagmax)
        weights = np.r_[np.arange(len(values) - 1, len(values) - len(covs) - 1, -1), np.finfo(float).max]
        blocks = pava_blocks(np.r_[covs, 0], weights, up=False)
        return np.r_[1, np.repeat(blocks["x"], blocks["blocks"].astype(int))]
    lagmax = min(len(values) - 1, len(values) - 1 if lagmax is None else lagmax)
    covs = _acf(values, lagmax - 1)[1:]
    fitted = _isoreg(np.r_[-covs, 0])
    return np.r_[1, -fitted]


def weightsLumley(x: Fit, order_by=None, C=None, method="truncate", acf=None, tol=1e-7, data=None, **_kwargs) -> np.ndarray:
    method = match_arg(method, ["truncate", "smooth"])
    if acf is None:
        acf = isoacf
    residuals = np.asarray(x.residuals, dtype=float).ravel()
    index = _order_index(len(residuals), order_by, data, x)
    residuals = residuals[index]
    rho = np.asarray(acf(residuals), dtype=float).ravel()
    if method == "truncate":
        if C is None:
            C = 4
        keep = np.flatnonzero(rho ** 2 * len(residuals) > C)
        lag = int(np.max(keep)) + 1 if len(keep) else 1
        return np.ones(lag)
    if C is None:
        C = 1
    weights = np.minimum(1, C * len(residuals) * rho ** 2)
    last = int(np.max(np.flatnonzero(np.abs(weights) > tol)))
    return weights[: last + 1]


def weave(x, order_by=None, prewhite=False, C=None, method="truncate", acf=None, adjust: bool = False, diagnostics: bool = False, sandwich_=True, tol=1e-7, data=None, **_kwargs) -> np.ndarray:
    def myweights(x, order_by=None, prewhite=False, data=None, **_ignored):
        return weightsLumley(x, order_by=order_by, C=C, method=method, acf=acf, tol=tol, data=data)

    return vcovHAC(x, order_by=order_by, prewhite=prewhite, weights=myweights, adjust=adjust, diagnostics=diagnostics, sandwich_=sandwich_, data=data)


def lrvar(x, type="Andrews", prewhite: bool = True, adjust: bool = True, **kwargs):
    values = np.asarray(coredata(x) if is_zoo(x) else x, dtype=float)
    if values.ndim == 1:
        values = values.reshape(-1, 1)
    names = ["(Intercept)"]
    response_names = None if values.shape[1] == 1 else [f"y{i+1}" for i in range(values.shape[1])]
    from .model import lm_fit

    fit = lm_fit(np.ones((values.shape[0], 1)), values.ravel() if values.shape[1] == 1 else values, names, responses=response_names)
    chosen = match_arg(type.replace("-", "").lower(), ["andrews", "neweywest"])
    if chosen == "andrews":
        estimate = kernHAC(fit, prewhite=prewhite, adjust=adjust, **kwargs)
    else:
        estimate = NeweyWest(fit, prewhite=prewhite, adjust=adjust, **kwargs)
    if values.shape[1] == 1:
        return float(np.asarray(estimate).reshape(-1)[0])
    return estimate
