"""Python translation of the R package lmtest.

A one-column regressor is given an intercept, matching ``y ~ x``.
The Durbin-Watson probability is Farebrother's pan in the Rust crate.
Granger lags use zoo's lag and merge. ``as.zoo`` on a plain vector is the
zoo constructor with index ``1:n``; that constructor is not edited here.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import stats

from extradistr._rng import norm_rand
from extradistr._special import pnorm
from pan import pan_prob
from zoo.merge import merge_zoo
from zoo.series import Zoo
from zoo.window import lag_zoo

__all__ = [
    "bgtest",
    "bptest",
    "coefci",
    "coeftest",
    "coxtest",
    "dwtest",
    "encomptest",
    "gqtest",
    "grangertest",
    "harvtest",
    "hmctest",
    "jtest",
    "lrtest",
    "petest",
    "raintest",
    "reset",
    "resettest",
    "waldtest",
]


def _column(x: Any) -> np.ndarray:
    values = np.asarray(x, dtype=float)
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim == 1:
        return values.reshape(-1, 1)
    return np.array(values, dtype=float, copy=True)


def _design(x: Any, intercept: bool = True) -> np.ndarray:
    """Regressors as a matrix. A single column gains an intercept."""
    values = _column(x)
    if intercept and values.shape[1] == 1:
        ones = np.ones((values.shape[0], 1))
        return np.column_stack([ones, values])
    return values


def _has_intercept(x: np.ndarray) -> bool:
    return x.shape[1] > 0 and np.allclose(x[:, 0], 1.0)


def _ols(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """Ordinary least squares through a QR, matching ``lm.fit`` on a full-rank matrix."""
    y = np.asarray(y, dtype=float).reshape(-1)
    q, r = np.linalg.qr(x, mode="reduced")
    sign = np.sign(np.diag(r))
    sign[sign == 0.0] = 1.0
    q = q * sign
    r = sign[:, None] * r
    beta = np.linalg.solve(r, q.T @ y)
    fitted = x @ beta
    resid = y - fitted
    rank = int(np.sum(np.abs(np.diag(r)) > 1e-12))
    return {
        "coefficients": beta,
        "fitted": fitted,
        "residuals": resid,
        "rank": rank,
        "df_residual": int(y.size - rank),
        "r": r,
    }


def _xtx_inv(x: np.ndarray) -> np.ndarray:
    gram = x.T @ x
    return np.linalg.inv(gram)


def _vcov(fit: dict[str, Any], x: np.ndarray) -> np.ndarray:
    df = fit["df_residual"]
    sigma2 = float(np.sum(fit["residuals"] ** 2) / df)
    return sigma2 * _xtx_inv(x)


def _order_rows(x: np.ndarray, y: np.ndarray, order_by: Any) -> tuple[np.ndarray, np.ndarray]:
    if order_by is None:
        return x, y
    keys = np.asarray(order_by, dtype=float).reshape(-1)
    order = np.argsort(keys, kind="mergesort")
    return x[order], y[order]


def _scale(y: np.ndarray, center: bool) -> np.ndarray:
    """R ``scale``: subtract the mean when requested, then divide by the sample sd."""
    out = np.asarray(y, dtype=float).reshape(-1).copy()
    if center:
        out = out - out.mean()
    sd = math.sqrt(float(np.sum(out**2) / (out.size - 1)))
    return out / sd


def _f_sf(stat: float, df1: float, df2: float) -> float:
    return float(stats.f.sf(stat, df1, df2))


def _chi_sf(stat: float, df: float) -> float:
    return float(stats.chi2.sf(stat, df))


def _t_sf(stat: float, df: float) -> float:
    return float(stats.t.sf(stat, df))


def dwtest(
    y: Any,
    x: Any,
    alternative: str = "greater",
    iterations: int = 15,
    exact: bool | None = None,
    tol: float = 1e-10,
    order_by: Any = None,
) -> dict[str, Any]:
    """Durbin-Watson test. The exact probability is Farebrother's pan."""
    if alternative not in ("greater", "two.sided", "less"):
        raise ValueError("alternative must be greater, two.sided, or less")
    y = np.asarray(y, dtype=float).reshape(-1)
    design = _design(x)
    design, y = _order_rows(design, y, order_by)
    n, k = design.shape
    if exact is None:
        exact = n < 100
    resid = _ols(design, y)["residuals"]
    dw = float(np.sum(np.diff(resid) ** 2) / np.sum(resid**2))
    q1 = _xtx_inv(design)
    if n < 3:
        pval = 1.0
        exact = False
    else:
        if exact:
            band = np.diag(np.concatenate([[1.0], np.full(n - 2, 2.0), [1.0]]))
            band[np.abs(np.subtract.outer(np.arange(n), np.arange(n))) == 1] = -1.0
            eye = np.eye(n)
            ma = (eye - design @ q1 @ design.T) @ band
            values = np.linalg.eigvals(ma)
            ordered = np.sort(np.real(values))[::-1]
            ev = ordered[: n - k]
            ev = ev[ev > tol]
            def pdw(stat: float) -> float:
                weights = np.concatenate([[stat], ev])
                return float(pan_prob(weights.tolist(), 0.0, int(iterations)))

            if alternative == "two.sided":
                pval = 2.0 * min(pdw(dw), 1.0 - pdw(dw))
            elif alternative == "less":
                pval = 1.0 - pdw(dw)
            else:
                pval = pdw(dw)
            if not math.isfinite(pval) or pval > 1.0 or pval < 0.0:
                exact = False
        if not exact:
            if n < max(5, k):
                pval = 1.0
            else:
                ax = np.full_like(design, np.nan)
                ax[1:-1] = -design[:-2] + 2.0 * design[1:-1] - design[2:]
                ax[0] = design[0] - design[1]
                ax[-1] = design[-1] - design[-2]
                xaxq = design.T @ ax @ q1
                p_trace = 2 * (n - 1) - float(np.trace(xaxq))
                q_trace = (
                    2 * (3 * n - 4)
                    - 2 * float(np.trace((ax.T @ ax) @ q1))
                    + float(np.trace(xaxq @ xaxq))
                )
                dmean = p_trace / (n - k)
                dvar = 2 / ((n - k) * (n - k + 2)) * (q_trace - p_trace * dmean)
                sd = math.sqrt(dvar)
                if alternative == "two.sided":
                    pval = 2.0 * pnorm(abs(dw - dmean), sd=sd, lower_tail=False)
                elif alternative == "less":
                    pval = pnorm(dw, mean=dmean, sd=sd, lower_tail=False)
                else:
                    pval = pnorm(dw, mean=dmean, sd=sd)
    text = {
        "two.sided": "true autocorrelation is not 0",
        "less": "true autocorrelation is less than 0",
        "greater": "true autocorrelation is greater than 0",
    }[alternative]
    return {
        "statistic": dw,
        "p_value": float(pval),
        "method": "Durbin-Watson test",
        "alternative": text,
    }


def bptest(y: Any, x: Any, z: Any = None, studentize: bool = True) -> dict[str, Any]:
    """Breusch-Pagan test. ``z`` is the variance regressor; it defaults to ``x``."""
    y = np.asarray(y, dtype=float).reshape(-1)
    design = _design(x)
    variance = design if z is None else _design(z)
    if variance.shape[1] < 2:
        raise ValueError(
            "the auxiliary variance regression requires at least an intercept and a regressor"
        )
    n = design.shape[0]
    weights = np.ones(n)
    resid = _ols(design, y)["residuals"]
    sigma2 = float(np.sum(weights * resid**2) / n)
    if studentize:
        target = resid**2 - sigma2
        aux = _ols(variance, target)
        bp = n * float(np.sum(weights * aux["fitted"] ** 2) / np.sum(target**2))
        method = "studentized Breusch-Pagan test"
    else:
        target = resid**2 / sigma2 - 1.0
        aux = _ols(variance, target)
        bp = 0.5 * float(np.sum(weights * aux["fitted"] ** 2))
        method = "Breusch-Pagan test"
    df = aux["rank"] - 1
    return {
        "statistic": bp,
        "parameter": df,
        "p_value": _chi_sf(bp, df),
        "method": method,
    }


def bgtest(
    y: Any,
    x: Any,
    order: int = 1,
    type: str = "Chisq",
    fill: float = 0.0,
    order_by: Any = None,
) -> dict[str, Any]:
    """Breusch-Godfrey test for serial correlation up to ``order``."""
    if type not in ("Chisq", "F"):
        raise ValueError("type must be Chisq or F")
    y = np.asarray(y, dtype=float).reshape(-1)
    design = _design(x)
    design, y = _order_rows(design, y, order_by)
    n, k = design.shape
    lags = list(range(1, order + 1))
    resid = _ols(design, y)["residuals"]
    columns = []
    for lag in lags:
        column = np.concatenate([np.full(lag, fill), resid[: n - lag]])
        columns.append(column)
    z = np.column_stack(columns)
    missing = ~np.all(np.isfinite(z), axis=1)
    if np.any(missing):
        keep = ~missing
        design = design[keep]
        z = z[keep]
        y = y[keep]
        resid = resid[keep]
        n = design.shape[0]
    aux = _ols(np.column_stack([design, z]), resid)
    m = len(lags)
    if type == "Chisq":
        bg = n * float(np.sum(aux["fitted"] ** 2) / np.sum(resid**2))
        df: Any = m
        pval = _chi_sf(bg, m)
    else:
        uresid = aux["residuals"]
        bg = ((np.sum(resid**2) - np.sum(uresid**2)) / m) / (
            np.sum(uresid**2) / (n - k - m)
        )
        df = (m, n - k - m)
        pval = _f_sf(float(bg), df[0], df[1])
    return {
        "statistic": float(bg),
        "parameter": df,
        "p_value": float(pval),
        "method": f"Breusch-Godfrey test for serial correlation of order up to {max(lags)}",
    }


def gqtest(
    y: Any,
    x: Any,
    point: float = 0.5,
    fraction: float = 0.0,
    alternative: str = "greater",
    order_by: Any = None,
) -> dict[str, Any]:
    """Goldfeld-Quandt test that the variance changes at ``point``."""
    if alternative not in ("greater", "two.sided", "less"):
        raise ValueError("alternative must be greater, two.sided, or less")
    y = np.asarray(y, dtype=float).reshape(-1)
    design = _design(x)
    k = design.shape[1]
    n = design.shape[0]
    if point > 1:
        if fraction < 1:
            fraction = math.floor(fraction * n)
        point1 = point - math.ceil(fraction / 2)
        point2 = point + math.ceil(fraction / 2 + 0.01)
    else:
        if fraction >= 1:
            fraction = fraction / n
        point1 = math.floor((point - fraction / 2) * n)
        point2 = math.ceil((point + fraction / 2) * n + 0.01)
    point1 = int(point1)
    point2 = int(point2)
    if point2 > n - k + 1 or point1 < k:
        raise ValueError("inadmissable breakpoint/too many central observations omitted")
    design, y = _order_rows(design, y, order_by)
    rss1 = float(np.sum(_ols(design[:point1], y[:point1])["residuals"] ** 2))
    rss2 = float(np.sum(_ols(design[point2 - 1 :], y[point2 - 1 :])["residuals"] ** 2))
    mss = (rss1 / (point1 - k), rss2 / (n - point2 + 1 - k))
    gq = mss[1] / mss[0]
    df1 = n - point2 + 1 - k
    df2 = point1 - k
    lower = float(stats.f.cdf(gq, df1, df2))
    upper = _f_sf(gq, df1, df2)
    if alternative == "two.sided":
        pval = 2.0 * min(lower, upper)
    elif alternative == "less":
        pval = lower
    else:
        pval = upper
    text = {
        "two.sided": "variance changes from segment 1 to 2",
        "less": "variance decreases from segment 1 to 2",
        "greater": "variance increases from segment 1 to 2",
    }[alternative]
    return {
        "statistic": float(gq),
        "parameter": (df1, df2),
        "p_value": float(pval),
        "method": "Goldfeld-Quandt test",
        "alternative": text,
    }


def _powers(values: np.ndarray, power: Any, n: int) -> np.ndarray:
    powers = np.atleast_1d(np.asarray(power, dtype=float))
    columns = [values**p for p in powers]
    return np.column_stack(columns)


def resettest(
    y: Any,
    x: Any,
    power: Any = (2, 3),
    type: str = "fitted",
) -> dict[str, Any]:
    """RESET test. ``type`` is fitted, regressor, or princomp."""
    if type not in ("fitted", "regressor", "princomp"):
        raise ValueError("type must be fitted, regressor, or princomp")
    y = np.asarray(y, dtype=float).reshape(-1)
    design = _design(x)
    raw = _column(x)
    y = _scale(y, center=_has_intercept(design))
    k = design.shape[1]
    n = design.shape[0]
    if type == "fitted":
        fitted = _ols(design, y)["fitted"]
        extra = _powers(fitted, power, n)
    elif type == "regressor":
        extra = _powers(raw.reshape(-1), power, n)
    else:
        centered = raw - raw.mean(axis=0)
        cov = np.cov(centered, rowvar=False, ddof=1)
        vector = np.linalg.eigh(np.atleast_2d(cov))[1][:, -1]
        score = raw @ vector
        extra = _powers(score, power, n)
    both = np.column_stack([design, extra])
    q = extra.shape[1]
    res1 = float(np.sum(_ols(design, y)["residuals"] ** 2))
    res2 = float(np.sum(_ols(both, y)["residuals"] ** 2))
    df1 = q
    df2 = n - (k + q)
    reset = (df2 / df1) * ((res1 - res2) / res2)
    return {
        "statistic": float(reset),
        "parameter": (df1, df2),
        "p_value": _f_sf(float(reset), df1, df2),
        "method": "RESET test",
    }


reset = resettest


def _recursive_residuals(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    n, q = x.shape
    w = np.zeros(n - q)
    xr1 = x[:q]
    xr = x[q].astype(float).copy()
    x1 = np.linalg.inv(xr1.T @ xr1)
    fr = 1.0 + float(xr @ x1 @ xr)
    beta = x1 @ xr1.T @ y[:q]
    w[0] = (y[q] - float(xr @ beta)) / math.sqrt(fr)
    for r in range(q + 1, n):
        x1 = x1 - (x1 @ np.outer(xr, xr) @ x1) / fr
        beta = beta + x1 @ xr * w[r - q - 1] * math.sqrt(fr)
        xr = x[r].astype(float).copy()
        fr = 1.0 + float(xr @ x1 @ xr)
        w[r - q] = (y[r] - float(xr @ beta)) / math.sqrt(fr)
    return w


def harvtest(y: Any, x: Any, order_by: Any = None) -> dict[str, Any]:
    """Harvey-Collier test on recursive residuals."""
    y = np.asarray(y, dtype=float).reshape(-1)
    design = _design(x)
    design, y = _order_rows(design, y, order_by)
    n, k = design.shape
    resr = _recursive_residuals(design, y)
    sigma = math.sqrt(float(np.var(resr, ddof=1)) * (resr.size - 1) / (n - k - 1))
    resr = resr / sigma
    harv = abs(float(np.sum(resr)) / math.sqrt(n - k)) / math.sqrt(float(np.var(resr, ddof=1)))
    df = n - k - 1
    return {
        "statistic": float(harv),
        "parameter": df,
        "p_value": 2.0 * _t_sf(float(harv), df),
        "method": "Harvey-Collier test",
    }


def coxtest(y: Any, x: Any, z: Any) -> dict[str, Any]:
    """Cox test of two non-nested linear models of the same response."""
    y = np.asarray(y, dtype=float).reshape(-1)
    design_x = _design(x)
    design_z = _design(z)
    x_fit = _ols(design_x, y)
    z_fit = _ols(design_z, y)
    s2x = float(np.mean(x_fit["residuals"] ** 2))
    s2z = float(np.mean(z_fit["residuals"] ** 2))
    zx = _ols(design_z, x_fit["fitted"])
    xz = _ols(design_x, z_fit["fitted"])
    s2zx = s2x + float(np.mean(zx["residuals"] ** 2))
    s2xz = s2z + float(np.mean(xz["residuals"] ** 2))
    xzx = _ols(design_x, zx["residuals"])
    zxz = _ols(design_z, xz["residuals"])
    s2xzx = float(np.mean(xzx["residuals"] ** 2))
    s2zxz = float(np.mean(zxz["residuals"] ** 2))
    n = design_x.shape[0]
    c01 = n / 2 * math.log(s2z / s2zx)
    v01 = n * (s2x / (s2zx**2)) * s2xzx
    c10 = n / 2 * math.log(s2x / s2xz)
    v10 = n * (s2z / (s2xz**2)) * s2zxz
    stat01 = c01 / math.sqrt(v01)
    stat10 = c10 / math.sqrt(v10)
    rows = np.array(
        [
            [c01, math.sqrt(v01), stat01],
            [c10, math.sqrt(v10), stat10],
        ]
    )
    p = [
        2.0 * pnorm(abs(stat01), lower_tail=False),
        2.0 * pnorm(abs(stat10), lower_tail=False),
    ]
    return {"estimate": rows[:, 0], "std_error": rows[:, 1], "z": rows[:, 2], "p_value": np.array(p)}


def hmctest(
    y: Any,
    x: Any,
    point: float = 0.5,
    simulate_p: bool = True,
    nsim: int = 1000,
    order_by: Any = None,
) -> dict[str, Any]:
    """Harrison-McCabe test. Simulated p-values use R's normal generator."""
    y = np.asarray(y, dtype=float).reshape(-1)
    design = _design(x)
    design, y = _order_rows(design, y, order_by)
    n, k = design.shape
    if point < 1:
        point = math.floor(point * n)
    point = int(point)
    if point > n - k or point < k:
        raise ValueError("inadmissable breakpoint")
    resid = _ols(design, y)["residuals"]
    hmc = float(np.sum(resid[:point] ** 2) / np.sum(resid**2))
    if simulate_p:
        stat = np.empty(nsim)
        for i in range(nsim):
            draw = np.array([norm_rand() for _ in range(n)])
            draw = (draw - draw.mean()) / math.sqrt(float(np.var(draw, ddof=1)))
            stat[i] = np.sum(draw[:point] ** 2) / np.sum(draw**2)
        pval = float(np.mean(stat <= hmc))
    else:
        pval = float("nan")
    return {"statistic": hmc, "p_value": pval, "method": "Harrison-McCabe test"}


def _omitted_columns(full: np.ndarray, reduced: np.ndarray) -> np.ndarray:
    """Columns of the larger design that the smaller design does not contain."""
    used = np.zeros(full.shape[1], dtype=bool)
    for column in reduced.T:
        matched = False
        for j in range(full.shape[1]):
            if not used[j] and np.allclose(full[:, j], column):
                used[j] = True
                matched = True
                break
        if not matched:
            raise ValueError("nesting of models cannot be determined")
    return ~used


def _wald_rows(y: np.ndarray, full: np.ndarray, reduced: np.ndarray, test: str) -> dict[str, Any]:
    """Wald comparison of two nested designs. The second row tests the smaller model."""
    if full.shape[1] < reduced.shape[1]:
        full, reduced = reduced, full
    fit1 = _ols(full, y)
    fit0 = _ols(reduced, y)
    q = int(fit1["coefficients"].size - fit0["coefficients"].size)
    omitted = _omitted_columns(full, reduced)
    if int(np.sum(omitted)) != abs(q):
        raise ValueError("nesting of models cannot be determined")
    vc = _vcov(fit1, full)
    beta = fit1["coefficients"][omitted]
    piece = vc[np.ix_(omitted, omitted)]
    stat = float(beta @ np.linalg.solve(piece, beta))
    res_df = [fit1["df_residual"], fit0["df_residual"]]
    if q == 0:
        raise ValueError("empty model specification")
    if test == "Chisq":
        shown = stat
        pval = _chi_sf(stat, q)
        df = -q if fit1["coefficients"].size >= fit0["coefficients"].size else q
    else:
        shown = stat / q
        pval = _f_sf(shown, q, fit1["df_residual"])
        df = -q
    return {
        "res_df": res_df,
        "df": df,
        "statistic": shown,
        "p_value": float(pval),
    }


def waldtest(y: Any, x: Any, z: Any = None, test: str = "F") -> dict[str, Any]:
    """Wald test. With one regressor, the reference model is the intercept."""
    if test not in ("F", "Chisq"):
        raise ValueError("test must be F or Chisq")
    y = np.asarray(y, dtype=float).reshape(-1)
    full = _design(x)
    if z is None:
        reduced = np.ones((y.size, 1))
    else:
        reduced = _design(z)
    return _wald_rows(y, full, reduced, test)


def lrtest(y: Any, x: Any, z: Any = None) -> dict[str, Any]:
    """Likelihood-ratio test of two linear models. The reference is the intercept."""
    y = np.asarray(y, dtype=float).reshape(-1)
    full = _design(x)
    reduced = np.ones((y.size, 1)) if z is None else _design(z)
    fits = [_ols(full, y), _ols(reduced, y)]
    loglik = []
    dfs = []
    n = y.size
    for fit in fits:
        rss = float(np.sum(fit["residuals"] ** 2))
        k = fit["coefficients"].size
        loglik.append(-n / 2 * (math.log(2 * math.pi) + 1 - math.log(n) + math.log(rss)))
        dfs.append(k + 1)
    df = dfs[1] - dfs[0]
    chisq = 2 * abs(loglik[1] - loglik[0])
    return {
        "df_model": dfs,
        "loglik": loglik,
        "df": df,
        "statistic": chisq,
        "p_value": _chi_sf(chisq, abs(df)),
    }


def coeftest(y: Any, x: Any) -> dict[str, Any]:
    """t test of ordinary-least-squares coefficients."""
    y = np.asarray(y, dtype=float).reshape(-1)
    design = _design(x)
    fit = _ols(design, y)
    se = np.sqrt(np.diag(_vcov(fit, design)))
    estimate = fit["coefficients"]
    tval = estimate / se
    df = fit["df_residual"]
    pval = 2.0 * stats.t.sf(np.abs(tval), df)
    return {
        "estimate": estimate,
        "std_error": se,
        "t": tval,
        "p_value": pval,
        "df": df,
    }


def coefci(y: Any, x: Any, level: float = 0.95) -> np.ndarray:
    """Confidence interval for ordinary-least-squares coefficients."""
    tested = coeftest(y, x)
    a = (1.0 - level) / 2.0
    fac = stats.t.ppf([a, 1.0 - a], tested["df"])
    estimate = tested["estimate"]
    se = tested["std_error"]
    return np.column_stack([estimate + fac[0] * se, estimate + fac[1] * se])


def _last_coefficient(y: np.ndarray, design: np.ndarray) -> dict[str, Any]:
    """Coefficient test after dropping rows that ``lm`` would omit."""
    y = np.asarray(y, dtype=float).reshape(-1)
    mask = np.isfinite(y) & np.all(np.isfinite(design), axis=1)
    tested = coeftest(y[mask], design[mask])
    return {
        "estimate": tested["estimate"][-1],
        "std_error": tested["std_error"][-1],
        "t": tested["t"][-1],
        "p_value": tested["p_value"][-1],
    }


def jtest(y: Any, x: Any, z: Any) -> dict[str, Any]:
    """Davidson-MacKinnon J test. Each model is tested with the other's fitted values."""
    y = np.asarray(y, dtype=float).reshape(-1)
    design_x = _design(x)
    design_z = _design(z)
    fit_x = _ols(design_x, y)
    fit_z = _ols(design_z, y)
    first = _last_coefficient(y, np.column_stack([design_x, fit_z["fitted"]]))
    second = _last_coefficient(y, np.column_stack([design_z, fit_x["fitted"]]))
    return {
        "estimate": np.array([first["estimate"], second["estimate"]]),
        "std_error": np.array([first["std_error"], second["std_error"]]),
        "t": np.array([first["t"], second["t"]]),
        "p_value": np.array([first["p_value"], second["p_value"]]),
    }


def encomptest(y: Any, x: Any, z: Any) -> dict[str, Any]:
    """Encompassing test. Each model is compared with the union of the regressors."""
    y = np.asarray(y, dtype=float).reshape(-1)
    design_x = _design(x)
    design_z = _design(z)
    extra = design_z[:, 1:] if _has_intercept(design_z) else design_z
    encompassing = np.column_stack([design_x, extra])
    first = _wald_rows(y, encompassing, design_x, "F")
    second = _wald_rows(y, encompassing, design_z, "F")
    return {
        "res_df": [first["res_df"][0], second["res_df"][0]],
        "df": [first["df"], second["df"]],
        "statistic": [first["statistic"], second["statistic"]],
        "p_value": [first["p_value"], second["p_value"]],
    }


def petest(y: Any, x: Any, y2: Any, z: Any) -> dict[str, Any]:
    """PE test. One response is the log or the exp of the other."""
    y = np.asarray(y, dtype=float).reshape(-1)
    y2 = np.asarray(y2, dtype=float).reshape(-1)
    if np.allclose(y2, np.log(y)):
        islog1, islog2 = False, True
    elif np.allclose(np.log(y2), y):
        islog1, islog2 = True, False
    else:
        raise ValueError(
            "response in formula2 does not seem to specify the log or exp of the response in formula1"
        )
    design_x = _design(x)
    design_z = _design(z)
    hat1 = _ols(design_x, y)["fitted"]
    hat2 = _ols(design_z, y2)["fitted"]
    with np.errstate(invalid="ignore"):
        aux1 = hat2 - np.exp(hat1) if islog1 else np.log(hat1) - hat2
        aux2 = hat1 - np.exp(hat2) if islog2 else np.log(hat2) - hat1
    first = _last_coefficient(y, np.column_stack([design_x, aux1]))
    second = _last_coefficient(y2, np.column_stack([design_z, aux2]))
    return {
        "estimate": np.array([first["estimate"], second["estimate"]]),
        "std_error": np.array([first["std_error"], second["std_error"]]),
        "t": np.array([first["t"], second["t"]]),
        "p_value": np.array([first["p_value"], second["p_value"]]),
    }


def raintest(
    y: Any,
    x: Any,
    fraction: float = 0.5,
    order_by: Any = None,
    center: float | None = None,
) -> dict[str, Any]:
    """Rainbow test. The central fraction is the subset, ordered by ``order_by``."""
    y = np.asarray(y, dtype=float).reshape(-1)
    design = _design(x)
    n, k = design.shape
    if order_by is None:
        if center is None:
            center = 0.5
        if center > 1:
            center = center / n
        probs = center - fraction / 2
        quantile = float(np.quantile(np.arange(1, n + 1), probs))
        start = math.ceil(quantile)
        stop = start + math.floor(fraction * n) - 1
    else:
        design, y = _order_rows(design, y, order_by)
        if center is None:
            center = 0.5
        if center > 1:
            center = center / n
        probs = center - fraction / 2
        quantile = float(np.quantile(np.arange(1, n + 1), probs))
        start = math.ceil(quantile)
        stop = start + math.floor(fraction * n) - 1
    start = int(start)
    stop = int(stop)
    sub_x = design[start - 1 : stop]
    sub_y = y[start - 1 : stop]
    n1 = sub_x.shape[0]
    if n1 < k:
        raise ValueError("not enough observations in subset")
    sresi = float(np.sum(_ols(design, y)["residuals"] ** 2))
    sresi1 = float(np.sum(_ols(sub_x, sub_y)["residuals"] ** 2))
    rain = ((sresi - sresi1) / (n - n1)) / (sresi1 / (n1 - k))
    df1 = n - n1
    df2 = n1 - k
    return {
        "statistic": float(rain),
        "parameter": (df1, df2),
        "p_value": _f_sf(float(rain), df1, df2),
        "method": "Rainbow test",
    }


def _as_series(values: np.ndarray) -> Zoo:
    index = np.arange(1, values.size + 1, dtype=float)
    return Zoo(values.astype(float), index)


def _lag_block(series: Zoo, order: int) -> Zoo:
    parts = [lag_zoo(series, k=-k) for k in range(1, order + 1)]
    if len(parts) == 1:
        return parts[0]
    return merge_zoo(*parts)


def grangertest(x: Any, y: Any, order: int = 1) -> dict[str, Any]:
    """Granger test. ``y`` is the response and ``x`` is the series whose lags are added."""
    cause = np.asarray(x, dtype=float).reshape(-1)
    response = np.asarray(y, dtype=float).reshape(-1)
    cause_z = _as_series(cause)
    response_z = _as_series(response)
    merged = merge_zoo(
        cause_z,
        response_z,
        _lag_block(cause_z, order),
        _lag_block(response_z, order),
    )
    data = np.asarray(merged.data, dtype=float)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    data = data[np.all(np.isfinite(data), axis=1)]
    y_now = data[:, 1]
    lag_x = data[:, 2 : 2 + order]
    lag_y = data[:, 2 + order : 2 + 2 * order]
    full = np.column_stack([np.ones(y_now.size), lag_y, lag_x])
    reduced = np.column_stack([np.ones(y_now.size), lag_y])
    return _wald_rows(y_now, full, reduced, "F")
