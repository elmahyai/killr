"""Ordered logistic or probit regression (MASS polr)."""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from mass.errors import MassError

_METHODS = ("logistic", "probit", "loglog", "cloglog", "cauchit")

_EPS = 1.0e-80
_STEPREDN = 0.2
_ACCTOL = 0.0001
_RELTEST = 10.0


def _match_arg(value: str | None, choices: tuple[str, ...]) -> str:
    if value is None:
        return choices[0]
    text = str(value)
    exact = [item for item in choices if item == text]
    if len(exact) == 1:
        return exact[0]
    hits = [item for item in choices if item.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise MassError("'arg' should be one of " + ", ".join(repr(item) for item in choices))
    raise MassError("'arg' matched more than one choice: " + ", ".join(hits))


def _plogis(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    expx = np.exp(x[~pos])
    out[~pos] = expx / (1.0 + expx)
    return out


def _dlogis(x: np.ndarray) -> np.ndarray:
    p = _plogis(x)
    return p * (1.0 - p)


def _pnorm(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return 0.5 * (1.0 + np.vectorize(math.erf)(x / math.sqrt(2.0)))


def _dnorm(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return np.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _pcauchy(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return 0.5 + np.arctan(x) / math.pi


def _dcauchy(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return 1.0 / (math.pi * (1.0 + x * x))


def _pgumbel(q: np.ndarray, *, loc: float = 0.0, scale: float = 1.0, lower_tail: bool = True) -> np.ndarray:
    q = (np.asarray(q, dtype=float) - loc) / scale
    p = np.exp(-np.exp(-q))
    if not lower_tail:
        p = 1.0 - p
    return p


def _dgumbel(x: np.ndarray, *, loc: float = 0.0, scale: float = 1.0, log: bool = False) -> np.ndarray:
    x = (np.asarray(x, dtype=float) - loc) / scale
    d = math.log(1.0 / scale) - x - np.exp(-x)
    if log:
        return d
    return np.exp(d)


def _p_gumbel(q: np.ndarray, *, loc: float = 0.0, scale: float = 1.0, lower_tail: bool = True) -> np.ndarray:
    q = (np.asarray(q, dtype=float) - loc) / scale
    p = np.exp(-np.exp(q))
    if lower_tail:
        p = 1.0 - p
    return p


def _d_gumbel(x: np.ndarray, *, loc: float = 0.0, scale: float = 1.0, log: bool = False) -> np.ndarray:
    x = -(np.asarray(x, dtype=float) - loc) / scale
    d = math.log(1.0 / scale) - x - np.exp(-x)
    if log:
        return d
    return np.exp(d)


def _pfun(method: str, x: np.ndarray) -> np.ndarray:
    if method == "logistic":
        return _plogis(x)
    if method == "probit":
        return _pnorm(x)
    if method == "loglog":
        return _pgumbel(x, lower_tail=True)
    if method == "cloglog":
        return _p_gumbel(x, lower_tail=True)
    return _pcauchy(x)


def _dfun(method: str, x: np.ndarray) -> np.ndarray:
    if method == "logistic":
        return _dlogis(x)
    if method == "probit":
        return _dnorm(x)
    if method == "loglog":
        return _dgumbel(x, log=False)
    if method == "cloglog":
        return _d_gumbel(x, log=False)
    return _dcauchy(x)


def _vmmin(n0, b, fminfn, fmingr, maxit, trace, mask, abstol, reltol, n_report=10):
    """R stats BFGS vmmin; ``b`` is updated in place."""
    if maxit <= 0:
        return fminfn(b), 0
    if n_report <= 0:
        raise ValueError('REPORT must be > 0 (method = "BFGS")')
    free = [i for i in range(n0) if mask[i]]
    n = len(free)
    g = [0.0] * n0
    step = [0.0] * n
    point = [0.0] * n
    change = [0.0] * n
    inverse = [[0.0] * (i + 1) for i in range(n)]
    value = fminfn(b)
    if not math.isfinite(value):
        raise ValueError("initial value in 'vmmin' is not finite")
    if trace:
        sys.stdout.write("initial  value %f \n" % value)
    fmin = value
    gradcount = 1
    fmingr(b, g)
    iteration = 1
    ilast = gradcount
    count = 0
    counts = [1, gradcount]
    while True:
        if ilast == gradcount:
            for i in range(n):
                row = inverse[i]
                for j in range(i):
                    row[j] = 0.0
                row[i] = 1.0
        for i in range(n):
            point[i] = b[free[i]]
            change[i] = g[free[i]]
        gradproj = 0.0
        for i in range(n):
            total = 0.0
            row = inverse[i]
            for j in range(i + 1):
                total -= row[j] * g[free[j]]
            for j in range(i + 1, n):
                total -= inverse[j][i] * g[free[j]]
            step[i] = total
            gradproj += total * g[free[i]]
        if gradproj < 0.0:
            steplength = 1.0
            accepted = False
            while True:
                count = 0
                for i in range(n):
                    b[free[i]] = point[i] + steplength * step[i]
                    if (_RELTEST + point[i]) == (_RELTEST + b[free[i]]):
                        count += 1
                if count < n:
                    value = fminfn(b)
                    counts[0] += 1
                    accepted = math.isfinite(value) and (
                        value <= fmin + gradproj * steplength * _ACCTOL
                    )
                    if not accepted:
                        steplength *= _STEPREDN
                if count == n or accepted:
                    break
            enough = (value > abstol) and abs(value - fmin) > reltol * (abs(fmin) + reltol)
            if not enough:
                count = n
                fmin = value
            if count < n:
                fmin = value
                fmingr(b, g)
                gradcount += 1
                counts[1] = gradcount
                iteration += 1
                curvature = 0.0
                for i in range(n):
                    step[i] = steplength * step[i]
                    change[i] = g[free[i]] - change[i]
                    curvature += step[i] * change[i]
                if curvature > 0.0:
                    quad = 0.0
                    for i in range(n):
                        total = 0.0
                        row = inverse[i]
                        for j in range(i + 1):
                            total += row[j] * change[j]
                        for j in range(i + 1, n):
                            total += inverse[j][i] * change[j]
                        point[i] = total
                        quad += total * change[i]
                    quad = 1.0 + quad / curvature
                    for i in range(n):
                        row = inverse[i]
                        for j in range(i + 1):
                            row[j] += (
                                quad * step[i] * step[j]
                                - point[i] * step[j]
                                - step[i] * point[j]
                            ) / curvature
                else:
                    ilast = gradcount
            elif ilast < gradcount:
                count = 0
                ilast = gradcount
        else:
            count = 0
            if ilast == gradcount:
                count = n
            else:
                ilast = gradcount
        if trace and iteration % n_report == 0:
            sys.stdout.write("iter%4d value %f\n" % (iteration, value))
        if iteration >= maxit:
            break
        if gradcount - ilast > 2 * n:
            ilast = gradcount
        if count == n and ilast == gradcount:
            break
    if trace:
        sys.stdout.write("final  value %f \n" % fmin)
        if iteration < maxit:
            sys.stdout.write("converged\n")
        else:
            sys.stdout.write("stopped after %i iterations\n" % iteration)
    fail = 0 if iteration < maxit else 1
    return fmin, fail, counts


def _split_formula(formula: str) -> tuple[str, str]:
    if "~" not in formula:
        raise MassError("formula must contain ~")
    resp, rhs = formula.split("~", 1)
    return resp.strip(), rhs.strip()


def _parse_rhs_terms(rhs: str) -> tuple[bool, list[str]]:
    text = rhs.strip()
    intercept = True
    if text.startswith("0 +") or text.startswith("-1 +"):
        intercept = False
        text = text.split("+", 1)[1].strip()
    elif text.startswith("1 +"):
        text = text.split("+", 1)[1].strip()
    elif text == "0" or text == "1":
        return intercept, []
    terms: list[str] = []
    for piece in text.replace(" ", "").split("+"):
        if not piece or piece == "1":
            continue
        if piece == "0" or piece == "-1":
            intercept = False
            continue
        terms.append(piece)
    return intercept, terms


def _factor_levels(values: list[Any]) -> list[str]:
    seen: dict[str, None] = {}
    for item in values:
        seen[str(item)] = None
    return list(seen.keys())


def _make_names(prefix: str, level: str) -> str:
    text = f"{prefix}{level}"
    return text.replace(" ", ".")


def _model_matrix_polr(
    data: dict[str, Any],
    formula: str,
    *,
    response_levels: list[str] | None = None,
    predictor_levels: dict[str, list[str]] | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str], list[str]]:
    resp, rhs = _split_formula(formula)
    _intercept, terms = _parse_rhs_terms(rhs)
    if resp not in data:
        raise MassError(f"object '{resp}' not found")
    y_raw = data[resp]
    if isinstance(y_raw, str):
        y_raw = [y_raw]
    y_list = [str(v) for v in y_raw]
    n = len(y_list)
    lev = list(response_levels) if response_levels is not None else _factor_levels(y_list)
    pred_levels = predictor_levels or {}
    if len(lev) <= 2:
        raise MassError("response must have 3 or more levels")
    y = np.array([lev.index(v) + 1 for v in y_list], dtype=int)
    columns: list[np.ndarray] = []
    names: list[str] = []
    for term in terms:
        if term not in data:
            raise MassError(f"object '{term}' not found")
        col_raw = data[term]
        if isinstance(col_raw, str):
            col_raw = [col_raw]
        col_list = list(col_raw)
        if len(col_list) != n:
            raise MassError(f"variable '{term}' was created with size {len(col_list)}, not {n}")
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in col_list):
            col = np.asarray(col_list, dtype=float).reshape(-1)
            columns.append(col)
            names.append(term)
        else:
            levels = list(pred_levels.get(term, _factor_levels([str(v) for v in col_list])))
            for j, level in enumerate(levels[1:], start=1):
                dummy = np.array([1.0 if str(col_list[i]) == level else 0.0 for i in range(n)])
                columns.append(dummy)
                names.append(_make_names(term, level))
    x = np.column_stack(columns) if columns else np.empty((n, 0))
    return x, y, names, lev, []


def _qr_coef(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, int]:
    q, r = np.linalg.qr(x, mode="reduced")
    coef = np.linalg.solve(r, q.T @ y)
    rank = int(np.sum(np.abs(np.diag(r)) > np.max(x.shape) * np.finfo(float).eps))
    return coef, rank


def _glm_fit_start(
    x: np.ndarray,
    y: np.ndarray,
    *,
    link: str,
    weights: np.ndarray,
    offset: np.ndarray,
    maxit: int = 25,
    epsilon: float = 1e-8,
) -> tuple[np.ndarray, bool]:
    n = x.shape[0]
    prior = weights
    off = offset
    mu = (prior * y + 0.5) / (prior + 1.0)
    coef = np.zeros(x.shape[1])
    dev = math.inf
    converged = False
    for _ in range(maxit):
        if link == "logit":
            mu = np.clip(mu, 1e-12, 1 - 1e-12)
            eta = np.log(mu / (1.0 - mu))
            mu_eta = mu * (1.0 - mu)
            variance = mu * (1.0 - mu)
        elif link == "probit":
            mu = np.clip(mu, 1e-12, 1 - 1e-12)
            eta = np.vectorize(lambda p: math.sqrt(2.0) * _erfinv(2.0 * p - 1.0))(mu)
            mu_eta = _dnorm(eta)
            variance = mu * (1.0 - mu)
        else:
            mu = np.clip(mu, 1e-12, 1 - 1e-12)
            eta = np.tan(math.pi * (mu - 0.5))
            mu_eta = _dcauchy(eta)
            variance = mu * (1.0 - mu)
        working_weights = prior * (mu_eta**2) / variance
        working = (y - mu) / mu_eta
        z = eta - off + working
        scale = np.sqrt(working_weights)
        coef, _rank = _qr_coef(x * scale[:, None], z * scale)
        eta = x @ coef + off
        if link == "logit":
            mu = 1.0 / (1.0 + np.exp(-eta))
        elif link == "probit":
            mu = _pnorm(eta)
        else:
            mu = _pcauchy(eta)
        mu = np.clip(mu, 1e-12, 1 - 1e-12)
        term = np.zeros(n)
        pos = y > 0
        less = y < 1
        term[pos] += y[pos] * np.log(y[pos] / mu[pos])
        term[less] += (1.0 - y[less]) * np.log((1.0 - y[less]) / (1.0 - mu[less]))
        dev_new = float(2.0 * np.sum(prior * term))
        if abs(dev - dev_new) / (0.1 + abs(dev_new)) < epsilon:
            dev = dev_new
            converged = True
            break
        dev = dev_new
    return coef, converged


def _erfinv(y: float) -> float:
    if y <= -1.0:
        return -math.inf
    if y >= 1.0:
        return math.inf
    a = 0.147
    sgn = 1.0 if y >= 0 else -1.0
    y = abs(y)
    ln = math.log(1.0 - y * y)
    first = 2.0 / (math.pi * a) + ln / 2.0
    second = ln / a
    return sgn * math.sqrt(math.sqrt(first * first - second) - first)


def _jacobian_theta(theta: np.ndarray) -> np.ndarray:
    k = theta.size
    etheta = np.exp(theta)
    mat = np.zeros((k, k))
    mat[:, 0] = 1.0
    for i in range(1, k):
        mat[i:, i] = etheta[i]
    return mat


def polr_fit(
    x: np.ndarray,
    y: np.ndarray,
    wt: np.ndarray,
    start: np.ndarray,
    offset: np.ndarray,
    method: str,
    *,
    n_levels: int | None = None,
    control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pfun = lambda z: _pfun(method, z)
    dfun = lambda z: _dfun(method, z)
    n, pc = x.shape
    q = (int(y.max()) if n_levels is None else n_levels) - 1
    ind_pc = np.arange(pc)
    ind_q = np.arange(q)

    polr_y1 = (np.arange(1, q + 1)[None, :] == y[:, None]).astype(float)
    polr_y2 = (np.arange(1, q + 1)[None, :] == (y[:, None] - 1)).astype(float)

    def fmin(beta_list: list[float]) -> float:
        par = np.asarray(beta_list, dtype=float)
        beta = par[ind_pc]
        theta = par[pc : pc + q]
        zeta_inner = np.cumsum(np.concatenate(([theta[0]], np.exp(theta[1:]))))
        gamm = np.concatenate(([-math.inf], zeta_inner, [math.inf]))
        eta = offset.copy()
        if pc:
            eta = eta + x @ beta
        z1 = np.minimum(100.0, gamm[y] - eta)
        z2 = np.maximum(-100.0, gamm[y - 1] - eta)
        pr = pfun(z1) - pfun(z2)
        if np.all(pr > 0):
            return float(-np.sum(wt * np.log(pr)))
        return math.inf

    def gmin(beta_list: list[float], g_out: list[float]) -> None:
        par = np.asarray(beta_list, dtype=float)
        beta = par[ind_pc]
        theta = par[pc : pc + q]
        zeta_inner = np.cumsum(np.concatenate(([theta[0]], np.exp(theta[1:]))))
        gamm = np.concatenate(([-math.inf], zeta_inner, [math.inf]))
        eta = offset.copy()
        if pc:
            eta = eta + x @ beta
        z1 = np.minimum(100.0, gamm[y] - eta)
        z2 = np.maximum(-100.0, gamm[y - 1] - eta)
        pr = pfun(z1) - pfun(z2)
        p1 = dfun(z1)
        p2 = dfun(z2)
        if pc:
            g1 = x.T @ (wt * (p1 - p2) / pr)
        else:
            g1 = np.zeros(0)
        xx = polr_y1 * p1[:, None] - polr_y2 * p2[:, None]
        g2 = -(xx.T @ (wt / pr))
        g2 = g2 @ _jacobian_theta(theta)
        if np.all(pr > 0):
            grad = np.concatenate((g1, g2))
            for i in range(pc + q):
                g_out[i] = float(grad[i])
        else:
            for i in range(pc + q):
                g_out[i] = math.nan

    if pc:
        zeta_start = start[pc:]
        s0 = np.concatenate((start[: pc + 1], np.log(np.diff(zeta_start))))
    else:
        s0 = np.concatenate(([start[0]], np.log(np.diff(start))))
    par = [float(v) for v in s0]
    ctrl = {} if control is None else dict(control)
    maxit = int(ctrl.get("maxit", 100))
    reltol = float(ctrl.get("reltol", 1.490116e-08))
    abstol = float(ctrl.get("abstol", 0.0))
    trace = bool(ctrl.get("trace", 0))
    mask = [True] * len(par)

    def fmin_wrap(b):
        return fmin(b)

    def fmingr_wrap(b, g):
        gmin(b, g)

    value, fail, counts = _vmmin(len(par), par, fmin_wrap, fmingr_wrap, maxit, trace, mask, abstol, reltol)
    beta = np.asarray(par[:pc], dtype=float)
    theta = np.asarray(par[pc : pc + q], dtype=float)
    zeta = np.cumsum(np.concatenate(([theta[0]], np.exp(theta[1:]))))
    deviance = 2.0 * value
    return {
        "coefficients": beta,
        "zeta": zeta,
        "deviance": deviance,
        "convergence": fail,
        "counts": counts,
        "value": value,
    }


@dataclass
class PolrFit:
    coefficients: np.ndarray
    zeta: np.ndarray
    deviance: float
    fitted_values: np.ndarray
    lev: list[str]
    method: str
    convergence: int
    niter: dict[str, int]
    lp: np.ndarray
    edf: int
    df_residual: float
    n: float
    nobs: float
    formula: str
    model: dict[str, Any] | None = field(default=None)


def polr(
    formula: str,
    data: dict[str, Any],
    *,
    weights: Any = None,
    start: np.ndarray | list[float] | None = None,
    method: str | None = None,
    Hess: bool = False,
    model: bool = True,
    response_levels: list[str] | None = None,
    predictor_levels: dict[str, list[str]] | None = None,
    **control: Any,
) -> PolrFit:
    method = _match_arg(method, _METHODS)
    x, y, xnames, lev, _ = _model_matrix_polr(
        data,
        formula,
        response_levels=response_levels,
        predictor_levels=predictor_levels,
    )
    n = x.shape[0]
    pc = x.shape[1]
    q = len(lev) - 1
    if weights is None:
        wt = np.ones(n, dtype=float)
    else:
        wt = np.asarray(weights, dtype=float).reshape(-1)
        if wt.shape[0] != n:
            raise MassError("weights must have length equal to the number of observations")
    offset = np.zeros(n, dtype=float)
    if start is None:
        q1 = len(lev) // 2
        y1 = (y > q1).astype(float)
        x_int = np.column_stack((np.ones(n), x))
        link = "logit" if method == "logistic" else ("cauchit" if method == "cauchit" else "probit")
        coefs, converged = _glm_fit_start(x_int, y1, link=link, weights=wt, offset=offset)
        if not converged:
            raise MassError("attempt to find suitable starting values failed")
        if np.any(np.isnan(coefs)):
            import warnings

            warnings.warn("design appears to be rank-deficient, so dropping some coefs", stacklevel=2)
            keep = np.where(~np.isnan(coefs))[0]
            coefs = coefs[keep]
            if pc:
                keep_pred = [i - 1 for i in keep if i > 0]
                x = x[:, keep_pred]
                pc = x.shape[1]
                xnames = [xnames[i] for i in keep_pred]
        logit = lambda p: math.log(p / (1.0 - p))
        spacing = np.array([logit((k) / (q + 1)) for k in range(1, q + 1)])
        if method != "logistic":
            spacing = spacing / 1.7
        gammas = -coefs[0] + spacing - spacing[q1 - 1]
        start = np.concatenate((coefs[1:], gammas))
    else:
        start = np.asarray(start, dtype=float).reshape(-1)
        if start.size != pc + q:
            raise MassError("'start' is not of the correct length")
    fit = polr_fit(x, y, wt, start, offset, method, n_levels=len(lev), control=control or None)
    beta = fit["coefficients"]
    zeta = fit["zeta"]
    if pc:
        names = list(xnames)
        beta = beta.reshape(-1)
        beta_out = beta.copy()
        beta_out.setflags(write=False)
    else:
        names = []
        beta_out = beta
    zeta_names = [f"{lev[i]}|{lev[i + 1]}" for i in range(q)]
    zeta_out = zeta.copy()
    eta = offset + (x @ beta if pc else 0.0)
    pfun = lambda z: _pfun(method, z)
    cumpr = pfun(np.broadcast_to(zeta, (n, q)) - eta[:, None])
    fitted = np.diff(np.column_stack((np.zeros(n), cumpr, np.ones(n))), axis=1)
    counts = fit["counts"]
    niter = {"f.evals": counts[0], "g.evals": counts[1]}
    result = PolrFit(
        coefficients=np.asarray(beta_out, dtype=float),
        zeta=np.asarray(zeta_out, dtype=float),
        deviance=float(fit["deviance"]),
        fitted_values=fitted,
        lev=lev,
        method=method,
        convergence=int(fit["convergence"]),
        niter=niter,
        lp=np.asarray(eta, dtype=float),
        edf=pc + q,
        df_residual=float(np.sum(wt) - pc - q),
        n=float(np.sum(wt)),
        nobs=float(np.sum(wt)),
        formula=formula,
        model=data if model else None,
    )
    if names:
        result.coefficients = beta_out  # type: ignore[misc]
    _ = Hess  # Hessian not required for parity checks at default call
    return result


def polr_coef(fit: PolrFit) -> np.ndarray:
    return np.concatenate((fit.coefficients.reshape(-1), fit.zeta.reshape(-1)))


def polr_compare_vector(fit: PolrFit) -> np.ndarray:
    return np.concatenate((fit.coefficients.reshape(-1), fit.zeta.reshape(-1), [fit.deviance]))
