"""ARMA models by conditional least squares (tseries ``arma``)."""

from __future__ import annotations

import math
import warnings
import numpy as np

from tseries._num import embed, lm

try:
    from tsarma import arma_css as _arma_css
except ImportError:  # pragma: no cover
    _arma_css = None

_SQRT_EPS = math.sqrt(2.220446049250313e-16)


def _seq_n(n: int | None) -> list[int] | None:
    if n is None:
        return None
    n = int(n)
    if n <= 0:
        return None
    return list(range(1, n + 1))


def _nelder_mead(start, fn, maxit=500, abstol=float("-inf"), reltol=None, alpha=1.0, beta=0.5, gamma=2.0):
    """R ``optim`` Nelder-Mead (``nmmin``)."""
    if reltol is None:
        reltol = _SQRT_EPS
    n = len(start)
    point = [float(value) for value in start]
    big = 1.0e35
    if maxit <= 0:
        return {"par": point, "value": float(fn(point)), "convergence": 0}
    value = float(fn(point))
    if not math.isfinite(value):
        raise ValueError("function cannot be evaluated at initial parameters")
    columns = n + 2
    rows = n + 1
    simplex = [[0.0 for _ in range(columns)] for _ in range(rows)]
    funcount = 1
    convtol = reltol * (abs(value) + reltol)
    n1 = n + 1
    centroid_column = n + 1
    simplex[n][0] = value
    for i in range(n):
        simplex[i][0] = point[i]
    low = 1
    step = 0.0
    for i in range(n):
        candidate = 0.1 * abs(point[i])
        if candidate > step:
            step = candidate
    if step == 0.0:
        step = 0.1
    size = 0.0
    for j in range(2, n1 + 1):
        for i in range(n):
            simplex[i][j - 1] = point[i]
        trystep = step
        while simplex[j - 2][j - 1] == point[j - 2]:
            simplex[j - 2][j - 1] = point[j - 2] + trystep
            trystep *= 10
        size += trystep
    oldsize = size
    calcvert = True
    fail = 0
    while True:
        if calcvert:
            for j in range(n1):
                if j + 1 != low:
                    for i in range(n):
                        point[i] = simplex[i][j]
                    try:
                        value = float(fn(point))
                    except Exception:
                        value = big
                    if not math.isfinite(value):
                        value = big
                    funcount += 1
                    simplex[n][j] = value
            calcvert = False
        low_value = simplex[n][low - 1]
        high_value = low_value
        high = low
        for j in range(1, n1 + 1):
            if j != low:
                value = simplex[n][j - 1]
                if value < low_value:
                    low = j
                    low_value = value
                if value > high_value:
                    high = j
                    high_value = value
        if high_value <= low_value + convtol or low_value <= abstol:
            break
        for i in range(n):
            total = -simplex[i][high - 1]
            for j in range(n1):
                total += simplex[i][j]
            simplex[i][centroid_column] = total / n
        for i in range(n):
            point[i] = (1.0 + alpha) * simplex[i][centroid_column] - alpha * simplex[i][high - 1]
        try:
            value = float(fn(point))
        except Exception:
            value = big
        if not math.isfinite(value):
            value = big
        funcount += 1
        reflected = value
        if reflected < low_value:
            simplex[n][centroid_column] = value
            for i in range(n):
                expanded = gamma * point[i] + (1 - gamma) * simplex[i][centroid_column]
                simplex[i][centroid_column] = point[i]
                point[i] = expanded
            try:
                value = float(fn(point))
            except Exception:
                value = big
            if not math.isfinite(value):
                value = big
            funcount += 1
            if value < reflected:
                for i in range(n):
                    simplex[i][high - 1] = point[i]
                simplex[n][high - 1] = value
            else:
                for i in range(n):
                    simplex[i][high - 1] = simplex[i][centroid_column]
                simplex[n][high - 1] = reflected
        else:
            if reflected < high_value:
                for i in range(n):
                    simplex[i][high - 1] = point[i]
                simplex[n][high - 1] = reflected
            for i in range(n):
                point[i] = (1 - beta) * simplex[i][high - 1] + beta * simplex[i][centroid_column]
            try:
                value = float(fn(point))
            except Exception:
                value = big
            if not math.isfinite(value):
                value = big
            funcount += 1
            if value < simplex[n][high - 1]:
                for i in range(n):
                    simplex[i][high - 1] = point[i]
                simplex[n][high - 1] = value
            elif reflected >= high_value:
                calcvert = True
                size = 0.0
                for j in range(n1):
                    if j + 1 != low:
                        for i in range(n):
                            simplex[i][j] = beta * (simplex[i][j] - simplex[i][low - 1]) + simplex[i][low - 1]
                            size += abs(simplex[i][j] - simplex[i][low - 1])
                if size < oldsize:
                    oldsize = size
                else:
                    fail = 10
                    break
        if funcount > maxit:
            break
    result = [simplex[i][low - 1] for i in range(n)]
    if funcount > maxit:
        fail = 1
    return {
        "par": result,
        "value": simplex[n][low - 1],
        "convergence": fail,
    }


def _optim_hessian(fn, par, *, parscale=None, ndeps=None):
    n = len(par)
    if parscale is None:
        parscale = [1.0] * n
    if ndeps is None:
        ndeps = [0.001] * n

    def numeric_grad(point):
        g = [0.0] * n
        for i in range(n):
            eps = ndeps[i] * (abs(point[i]) + parscale[i])
            pp = point[:]
            pm = point[:]
            pp[i] += eps
            pm[i] -= eps
            g[i] = (fn(pp) - fn(pm)) / (2.0 * eps)
        return g

    hess = np.zeros((n, n), dtype=float)
    for i in range(n):
        eps = ndeps[i] * (abs(par[i]) + parscale[i])
        pp = par[:]
        pm = par[:]
        pp[i] += eps
        pm[i] -= eps
        gp = numeric_grad(pp)
        gm = numeric_grad(pm)
        for j in range(i, n):
            hess[i, j] = (gp[j] - gm[j]) / (2.0 * eps)
            if j != i:
                hess[j, i] = hess[i, j]
    return hess


def _qr_rank(matrix: np.ndarray, tol: float) -> int:
    """R ``qr(..., tol=)`` rank on a square Hessian."""
    mat = np.asarray(matrix, dtype=float)
    if mat.size == 0:
        return 0
    q, r = np.linalg.qr(mat)
    diag = np.abs(np.diag(r))
    threshold = tol * max(mat.shape[0], mat.shape[1]) * (diag.max() if diag.size else 0.0)
    return int(np.sum(diag > threshold))


def _ar_ols_resid(x: np.ndarray, order_max: int, *, intercept: bool) -> np.ndarray:
    """``stats::ar.ols`` residuals for a univariate series."""
    series = np.asarray(x, dtype=float).reshape(-1)
    n = len(series)
    order_max = int(round(order_max))
    y = embed(series, order_max + 1)
    current = y[:, 0]
    lags = y[:, 1:]
    if intercept:
        design = np.column_stack([np.ones(lags.shape[0]), lags])
    else:
        design = lags
    beta, _, _, _ = np.linalg.lstsq(design, current, rcond=None)
    fitted = design @ beta
    error = current - fitted
    resid = np.concatenate([np.full(order_max, np.nan), error])
    return resid


def _css_residuals(x, coef, lag_ar, lag_ma, max_order, include_intercept):
    if _arma_css is None:
        raise ImportError("tsarma extension is required for arma()")
    ar = np.asarray(lag_ar if lag_ar is not None else [], dtype=np.int32)
    ma = np.asarray(lag_ma if lag_ma is not None else [], dtype=np.int32)
    u = np.asarray(_arma_css(np.asarray(x, float), ar, ma, np.asarray(coef, float), include_intercept), float)
    max_order = int(max_order)
    if max_order > 0:
        u[:max_order] = 0.0
    return u


def _arma_init(x, lag_ar, lag_ma, max_order, include_intercept, n):
    k = int(round(1.1 * math.log(n)))
    resid = _ar_ols_resid(x, k, intercept=include_intercept)
    e = resid[~np.isnan(resid)]
    ee = embed(e, max_order + 1)
    xx = embed(x[k:], max_order + 1)
    y = xx[:, 0]
    parts = []
    if lag_ar is not None:
        parts.extend(xx[:, lag] for lag in lag_ar)
    if lag_ma is not None:
        parts.extend(ee[:, lag] for lag in lag_ma)
    design = np.column_stack(parts)
    if include_intercept:
        fit = lm(y, np.column_stack([np.ones(len(y)), design]))
        coef = np.concatenate([fit["coef"][1:], fit["coef"][:1]])
    else:
        fit = lm(y, design)
        coef = fit["coef"]
    return coef


def arma(
    x,
    order=(1, 1),
    lag=None,
    coef=None,
    include_intercept=True,
    series=None,
    qr_tol=1e-07,
    **optim_kwargs,
):
    if order is not None and lag is not None:
        warnings.warn("order is ignored", stacklevel=2)
    if order is None and lag is None:
        raise ValueError("order or lag must be given")
    if lag is None and order is not None:
        order = tuple(order)
        lag = {"ar": _seq_n(order[0]), "ma": _seq_n(order[1]) if len(order) > 1 else None}
    lag_ar = lag.get("ar") if isinstance(lag, dict) else lag["ar"]
    lag_ma = lag.get("ma") if isinstance(lag, dict) else lag["ma"]
    if lag_ar is not None:
        lag_ar = sorted(set(int(v) for v in lag_ar))
        if not lag_ar:
            lag_ar = None
    if lag_ma is not None:
        lag_ma = sorted(set(int(v) for v in lag_ma))
        if not lag_ma:
            lag_ma = None
    lag_parts = [part for part in (lag_ar, lag_ma) if part]
    max_order = max([0, *(v for group in lag_parts for v in group)])

    values = np.asarray(x, dtype=float)
    if values.ndim == 2 and values.shape[1] == 1:
        values = values.reshape(-1)
    if values.ndim != 1:
        raise ValueError("x is not a vector or univariate time series")
    if np.isnan(values).any():
        raise ValueError("NAs in x")
    n = len(values)
    if lag_parts:
        all_lags = [v for group in lag_parts for v in group]
        if min(all_lags) < 1 or max(all_lags) > n - 1:
            raise ValueError("invalid lag")
    ar_l = 0 if lag_ar is None else len(lag_ar)
    ma_l = 0 if lag_ma is None else len(lag_ma)
    ncoef = ar_l + ma_l + int(include_intercept)

    if coef is None:
        if lag_parts:
            coef = _arma_init(values, lag_ar, lag_ma, max_order, include_intercept, n)
        else:
            coef = np.zeros(1, dtype=float)
    coef = np.asarray(coef, dtype=float).reshape(-1)
    if coef.size != ncoef:
        raise ValueError("invalid coef")

    def err(candidate):
        u = _css_residuals(values, candidate, lag_ar, lag_ma, max_order, include_intercept)
        return float(np.dot(u, u))

    def resid_fn(candidate):
        return _css_residuals(values, candidate, lag_ar, lag_ma, max_order, include_intercept)

    control = optim_kwargs.pop("control", None) or {}
    maxit = int(control.get("maxit", 500))
    reltol = float(control.get("reltol", _SQRT_EPS))
    abstol = float(control.get("abstol", 0.0))
    md = _nelder_mead(coef.tolist(), err, maxit=maxit, reltol=reltol, abstol=abstol)
    coef = np.asarray(md["par"], dtype=float)
    hessian = _optim_hessian(err, coef.tolist())
    rank = _qr_rank(hessian, qr_tol)
    if rank != ncoef:
        vc = np.full((ncoef, ncoef), np.nan)
        warnings.warn("singular Hessian", stacklevel=2)
    else:
        vc = 2 * md["value"] / n * np.linalg.inv(hessian)
        if np.any(np.diag(vc) < 0):
            warnings.warn("Hessian negative-semidefinite", stacklevel=2)

    e = resid_fn(coef)
    if max_order > 0:
        e[:max_order] = np.nan
    f = values - e

    nam_ar = [f"ar{lag}" for lag in lag_ar] if lag_ar else []
    nam_ma = [f"ma{lag}" for lag in lag_ma] if lag_ma else []
    nam_int = ["intercept"] if include_intercept else []
    nam_coef = nam_ar + nam_ma + nam_int

    if series is None:
        series = "x"

    return {
        "coef": np.asarray(coef, dtype=float),
        "coef_names": nam_coef,
        "css": float(md["value"]),
        "n_used": n,
        "residuals": e,
        "fitted_values": f,
        "series": series,
        "frequency": 1.0,
        "vcov": vc,
        "lag": {"ar": lag_ar, "ma": lag_ma},
        "convergence": int(md["convergence"]),
        "include_intercept": include_intercept,
    }
