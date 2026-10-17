"""GLM diagnostics and cross-validation from boot 1.3-32.

Gaussian and binomial fits are IRLS in this module. ``glm.diag`` reads the
deviance, the Pearson residuals, and the leverages of the weighted least
squares step that met the convergence test. Those leverages are not the hat
values of the final mean.
"""

from __future__ import annotations

import math
import re
import warnings

import numpy as np

from boot.rng import sample_int

_DBL_EPS = float(np.finfo(np.float64).eps)
_THRESH = 30.0
_EPSILON = 1e-8
_MAXIT = 25
_QR_TOL = 1e-11

_LOG_RE = re.compile(r"log\((.+)\)\Z")
_LOG10_RE = re.compile(r"log10\((.+)\)\Z")


def _as_float(values) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def _columns(data: dict) -> dict[str, np.ndarray]:
    if not isinstance(data, dict) or not data:
        raise TypeError("data must be a non-empty dict of columns")
    columns = {name: _as_float(values) for name, values in data.items()}
    lengths = {array.shape for array in columns.values()}
    if len(lengths) != 1 or any(array.ndim != 1 for array in columns.values()):
        raise ValueError("data columns must be one-dimensional and the same length")
    return columns


def _nrow(data: dict) -> int:
    return int(next(iter(_columns(data).values())).shape[0])


def _subset(data: dict, index: np.ndarray) -> dict:
    columns = _columns(data)
    return {name: values[index] for name, values in columns.items()}


def _eval_expr(expr: str, columns: dict[str, np.ndarray]) -> np.ndarray:
    expr = expr.strip()
    match = _LOG_RE.fullmatch(expr)
    if match is not None:
        return np.log(_eval_expr(match.group(1), columns))
    match = _LOG10_RE.fullmatch(expr)
    if match is not None:
        return np.log10(_eval_expr(match.group(1), columns))
    if expr not in columns:
        raise KeyError(f"column {expr!r} is not in data")
    return columns[expr]


def _split_rhs(rhs: str) -> list[tuple[int, str]]:
    terms: list[tuple[int, str]] = []
    buf: list[str] = []
    depth = 0
    sign = 1
    for char in rhs.strip():
        if char == "(":
            depth += 1
            buf.append(char)
        elif char == ")":
            depth -= 1
            buf.append(char)
        elif char in "+-" and depth == 0:
            piece = "".join(buf).strip()
            if piece:
                terms.append((sign, piece))
            sign = 1 if char == "+" else -1
            buf = []
        else:
            buf.append(char)
    piece = "".join(buf).strip()
    if piece:
        terms.append((sign, piece))
    return terms


def _model_matrix(formula: str, data: dict) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if "~" not in formula:
        raise ValueError("formula must contain '~'")
    left, right = formula.split("~", 1)
    columns = _columns(data)
    y = _eval_expr(left, columns)
    intercept = True
    names = ["(Intercept)"]
    cols: list[np.ndarray] = []
    for sign, term in _split_rhs(right):
        if term in {"1", "0"}:
            intercept = sign == 1 and term == "1"
            continue
        if sign < 0:
            raise ValueError(f"cannot subtract term {term!r}")
        cols.append(_eval_expr(term, columns))
        names.append(term)
    n = y.shape[0]
    pieces = []
    if intercept:
        pieces.append(np.ones(n, dtype=np.float64))
    else:
        names = names[1:]
    pieces.extend(cols)
    if not pieces:
        x = np.zeros((n, 0), dtype=np.float64)
    else:
        x = np.column_stack(pieces)
    return y, x, names


def _logit(mu: np.ndarray) -> np.ndarray:
    return np.log(mu / (1.0 - mu))


def _logit_linkinv(eta: np.ndarray) -> np.ndarray:
    eta = _as_float(eta)
    out = np.empty(eta.shape, dtype=np.float64)
    low = eta < -_THRESH
    high = eta > _THRESH
    mid = ~low & ~high
    out[low] = _DBL_EPS
    out[high] = 1.0 - _DBL_EPS
    if np.any(mid):
        exponent = eta[mid]
        out[mid] = np.exp(exponent) / (1.0 + np.exp(exponent))
    return out


def _logit_mu_eta(eta: np.ndarray) -> np.ndarray:
    eta = _as_float(eta)
    out = np.empty(eta.shape, dtype=np.float64)
    clip = (eta > _THRESH) | (eta < -_THRESH)
    out[clip] = _DBL_EPS
    if np.any(~clip):
        exponent = eta[~clip]
        one_plus = 1.0 + np.exp(exponent)
        out[~clip] = np.exp(exponent) / (one_plus * one_plus)
    return out


def _mu_eta(family: str, eta: np.ndarray) -> np.ndarray:
    if family == "gaussian":
        return np.ones(eta.shape, dtype=np.float64)
    if family == "binomial":
        return _logit_mu_eta(eta)
    raise ValueError(f"family must be 'gaussian' or 'binomial', not {family!r}")


def _linkinv(family: str, eta: np.ndarray) -> np.ndarray:
    if family == "gaussian":
        return _as_float(eta)
    if family == "binomial":
        return _logit_linkinv(eta)
    raise ValueError(f"family must be 'gaussian' or 'binomial', not {family!r}")


def _variance(family: str, mu: np.ndarray) -> np.ndarray:
    if family == "gaussian":
        return np.ones(mu.shape, dtype=np.float64)
    if family == "binomial":
        return mu * (1.0 - mu)
    raise ValueError(f"family must be 'gaussian' or 'binomial', not {family!r}")


def _binom_dev_resids(y: np.ndarray, mu: np.ndarray, wt: np.ndarray) -> np.ndarray:
    y = _as_float(y)
    mu = _as_float(mu)
    wt = _as_float(wt)
    out = np.empty(y.shape, dtype=np.float64)
    at_zero = y == 0.0
    at_one = y == 1.0
    middle = ~at_zero & ~at_one
    out[at_zero] = -2.0 * wt[at_zero] * np.log(1.0 - mu[at_zero])
    out[at_one] = -2.0 * wt[at_one] * np.log(mu[at_one])
    if np.any(middle):
        yy = y[middle]
        mm = mu[middle]
        out[middle] = 2.0 * wt[middle] * (
            yy * np.log(yy / mm) + (1.0 - yy) * np.log((1.0 - yy) / (1.0 - mm))
        )
    return out


def _dev_resids(family: str, y: np.ndarray, mu: np.ndarray, wt: np.ndarray) -> np.ndarray:
    if family == "gaussian":
        return wt * (y - mu) ** 2
    if family == "binomial":
        return _binom_dev_resids(y, mu, wt)
    raise ValueError(f"family must be 'gaussian' or 'binomial', not {family!r}")


def _start(family: str, y: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if family == "gaussian":
        mu = y.copy()
        return mu, mu.copy()
    if family == "binomial":
        mu = (weights * y + 0.5) / (weights + 1.0)
        eta = _logit(mu)
        return _logit_linkinv(eta), eta
    raise ValueError(f"family must be 'gaussian' or 'binomial', not {family!r}")


def _weighted_fit(x: np.ndarray, z: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, int, np.ndarray]:
    """Least squares of z on x with weights w**2, and the hat diagonal."""
    design = x * w[:, None]
    q_factor, r_factor = np.linalg.qr(design, mode="reduced")
    n_coef = design.shape[1]
    if n_coef == 0:
        return np.zeros(0), 0, np.zeros(design.shape[0])
    diagonal = np.abs(np.diag(r_factor))
    scale = diagonal[0] if diagonal[0] > 0.0 else 1.0
    rank = int(np.sum(diagonal > _QR_TOL * scale))
    qty = q_factor.T @ (z * w)
    beta = np.zeros(n_coef, dtype=np.float64)
    if rank == n_coef:
        beta = np.linalg.solve(r_factor, qty)
    elif rank > 0:
        beta_s, _, rank_s, _ = np.linalg.lstsq(design, z * w, rcond=_QR_TOL)
        beta = beta_s
        rank = int(rank_s)
    hat = np.sum(q_factor[:, :rank] ** 2, axis=1) if rank else np.zeros(design.shape[0])
    limit = 1.0 - 10.0 * _DBL_EPS
    hat = np.minimum(hat, 1.0)
    hat[hat > limit] = 1.0
    return beta, rank, hat


class GlmFit:
    """Gaussian or binomial fit. Attributes follow the pieces ``glm.diag`` reads."""

    def __init__(
        self,
        formula: str,
        family: str,
        y: np.ndarray,
        coefficients: np.ndarray,
        fitted_values: np.ndarray,
        linear_predictors: np.ndarray,
        prior_weights: np.ndarray,
        working_weights: np.ndarray,
        deviance: float,
        df_residual: int,
        rank: int,
        hat: np.ndarray,
        residuals: np.ndarray,
    ):
        self.formula = formula
        self.family = family
        self.y = y
        self.coefficients = coefficients
        self.fitted_values = fitted_values
        self.linear_predictors = linear_predictors
        self.prior_weights = prior_weights
        self.weights = working_weights
        self.deviance = deviance
        self.df_residual = df_residual
        self.rank = rank
        self.hat = hat
        self.residuals = residuals


def glm(formula: str, data: dict, family: str = "gaussian", weights=None) -> GlmFit:
    """Fit a gaussian identity or binomial logit model by IRLS.

    ``formula`` uses ``~``, ``+``, ``log()``, and ``log10()``. An intercept is
    included unless the right-hand side contains ``-1`` or ``+0``.
    """
    if family not in {"gaussian", "binomial"}:
        raise ValueError(f"family must be 'gaussian' or 'binomial', not {family!r}")
    y, x, _names = _model_matrix(formula, data)
    n_obs, n_vars = x.shape
    if weights is None:
        prior = np.ones(n_obs, dtype=np.float64)
    else:
        prior = _as_float(weights)
        if prior.shape != (n_obs,):
            raise ValueError("weights must have one value per row")
    mu, eta = _start(family, y, prior)
    dev_old = float(np.sum(_dev_resids(family, y, mu, prior)))
    dev = dev_old
    beta = np.zeros(n_vars, dtype=np.float64)
    beta_old = None
    rank = 0
    hat = np.zeros(n_obs, dtype=np.float64)
    working = np.zeros(n_obs, dtype=np.float64)
    offset = np.zeros(n_obs, dtype=np.float64)
    converged = False
    for _iteration in range(1, _MAXIT + 1):
        mu_eta_val = _mu_eta(family, eta)
        variance = _variance(family, mu)
        good = (prior > 0.0) & (mu_eta_val != 0.0) & np.isfinite(variance) & (variance != 0.0)
        if not np.any(good):
            break
        z = (eta - offset)[good] + (y[good] - mu[good]) / mu_eta_val[good]
        w = np.sqrt(prior[good] * mu_eta_val[good] ** 2 / variance[good])
        beta, rank, hat_good = _weighted_fit(x[good], z, w)
        eta = x @ beta + offset
        mu = _linkinv(family, eta)
        dev = float(np.sum(_dev_resids(family, y, mu, prior)))
        if not np.isfinite(dev):
            if beta_old is None:
                break
            for _half in range(_MAXIT):
                beta = 0.5 * (beta + beta_old)
                eta = x @ beta + offset
                mu = _linkinv(family, eta)
                dev = float(np.sum(_dev_resids(family, y, mu, prior)))
                if np.isfinite(dev):
                    break
        # Keep the QR from this iteration. glm.diag's leverages are those
        # weights, including on the iteration that first satisfies the test.
        working[:] = 0.0
        working[good] = w ** 2
        hat[:] = 0.0
        hat[good] = hat_good
        if abs(dev - dev_old) / (0.1 + abs(dev)) < _EPSILON:
            converged = True
            break
        dev_old = dev
        beta_old = beta.copy()
    if not converged:
        warnings.warn("glm.fit: algorithm did not converge", stacklevel=2)
    n_ok = int(n_obs - np.sum(prior == 0.0))
    df_residual = int(n_ok - rank)
    fitted = mu
    with np.errstate(divide="ignore", invalid="ignore"):
        working_resid = (y - fitted) / _mu_eta(family, eta)
    return GlmFit(
        formula=formula,
        family=family,
        y=y,
        coefficients=beta,
        fitted_values=fitted,
        linear_predictors=eta,
        prior_weights=prior,
        working_weights=working,
        deviance=float(dev),
        df_residual=df_residual,
        rank=int(rank),
        hat=hat,
        residuals=working_resid,
    )


def _family_name(fit: GlmFit) -> str:
    family = fit.family
    if family not in {"gaussian", "binomial"}:
        raise ValueError(f"family must be 'gaussian' or 'binomial', not {family!r}")
    return family


def _deviance_residuals(fit: GlmFit) -> np.ndarray:
    mu = fit.fitted_values
    if fit.df_residual <= 0:
        return np.zeros(mu.shape, dtype=np.float64)
    pieces = np.sqrt(np.maximum(_dev_resids(_family_name(fit), fit.y, mu, fit.prior_weights), 0.0))
    return np.where(fit.y > mu, pieces, -pieces)


def _pearson_residuals(fit: GlmFit) -> np.ndarray:
    mu = fit.fitted_values
    return (fit.y - mu) * np.sqrt(fit.prior_weights) / np.sqrt(_variance(_family_name(fit), mu))


def glm_diag(glmfit: GlmFit) -> dict:
    """Jackknife, deviance, and Pearson residuals, Cook statistics, and leverages.

    Matches ``glm.diag`` for a gaussian or binomial fit. ``h`` is zero where
    the prior weight is zero. Other families are not fitted here; the Gaussian
    dispersion and the unit dispersion of every other family follow the R switch.
    """
    prior = np.asarray(glmfit.prior_weights, dtype=np.float64)
    family = _family_name(glmfit)
    if family == "gaussian":
        sd = math.sqrt(glmfit.deviance / glmfit.df_residual)
    else:
        sd = 1.0
    dev = _deviance_residuals(glmfit) / sd
    pear = _pearson_residuals(glmfit) / sd
    h = np.zeros(prior.shape, dtype=np.float64)
    keep = prior != 0.0
    h[keep] = np.asarray(glmfit.hat, dtype=np.float64)[keep]
    rank = glmfit.rank
    with np.errstate(divide="ignore", invalid="ignore"):
        rp = pear / np.sqrt(1.0 - h)
        rd = dev / np.sqrt(1.0 - h)
        cook = (h * rp ** 2) / ((1.0 - h) * rank)
        res = np.sign(dev) * np.sqrt(dev ** 2 + h * rp ** 2)
    return {"res": res, "rd": rd, "rp": rp, "cook": cook, "h": h, "sd": float(sd)}


def _ppoints(n: int) -> np.ndarray:
    a = 0.375 if n <= 10 else 0.5
    index = np.arange(1, n + 1, dtype=np.float64)
    return (index - a) / (n + 1.0 - 2.0 * a)


def _qnorm_acklam(p: float) -> float:
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
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
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p > 1.0 - plow:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )


def _qnorm_one(p: float) -> float:
    if p == 0.5:
        return 0.0
    if not 0.0 < p < 1.0:
        raise ValueError("qnorm probability must lie in (0, 1)")
    x = _qnorm_acklam(p)
    root = math.sqrt(2.0)
    for _ in range(4):
        cdf = 0.5 * math.erfc(-x / root)
        pdf = math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
        if pdf == 0.0:
            break
        x -= (cdf - p) / pdf
    return x


def _qnorm(p: np.ndarray) -> np.ndarray:
    return np.array([_qnorm_one(float(value)) for value in np.asarray(p, dtype=np.float64)])


def _rank_average(values: np.ndarray) -> np.ndarray:
    """R ``rank`` with ties.method 'average', ranks starting at 1."""
    values = _as_float(values)
    n = values.shape[0]
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(n, dtype=np.float64)
    ordered = values[order]
    start = 0
    while start < n:
        stop = start + 1
        while stop < n and ordered[stop] == ordered[start]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * ((start + 1) + stop)
        start = stop
    return ranks


def _case_index(subset, n_h: int, labels):
    if subset is None:
        return np.arange(1, n_h + 1, dtype=np.float64), labels
    if isinstance(subset, (str, bytes)):
        subset = [subset]
    values = np.asarray(subset)
    if values.dtype == bool or values.dtype == np.dtype(bool):
        return (np.flatnonzero(values) + 1).astype(np.float64), labels
    if values.dtype.kind in {"U", "S", "O"}:
        if labels is None:
            labels = [str(item) for item in values.tolist()]
        return np.arange(1, values.shape[0] + 1, dtype=np.float64), labels
    numbers = _as_float(values).ravel()
    if numbers.size and np.all(numbers < 0.0):
        length = numbers.size + n_h
        drop = {int(-item) for item in numbers}
        keep = [i for i in range(1, length + 1) if i not in drop]
        return np.asarray(keep, dtype=np.float64), labels
    return numbers, labels


def glm_diag_plots(
    glmfit: GlmFit,
    glmdiag: dict | None = None,
    subset=None,
    iden: bool = False,
    labels=None,
    ret: bool = False,
):
    """Four diagnostic panels for a gaussian or binomial fit.

    The panels follow ``glm.diag.plots``: jackknife residuals against the
    linear predictor, a normal QQ plot of the standardized deviance residuals,
    Cook's statistic against ``h/(1-h)``, and Cook's statistic against case
    number. ``iden=True`` is the interactive ``identify`` loop and is refused.
    ``ret=True`` returns the diagnostics after drawing.
    """
    if iden:
        raise ValueError("iden=True asks for interactive identify(), which is not available")
    if glmdiag is None:
        glmdiag = glm_diag(glmfit)
    cases, _labels = _case_index(subset, len(glmdiag["h"]), labels)
    import matplotlib.pyplot as plt

    _fig, axes = plt.subplots(2, 2, figsize=(7.0, 7.0))
    _fig.patch.set_facecolor("white")
    x1 = np.asarray(glmfit.linear_predictors, dtype=np.float64)
    point = dict(
        linestyle="None",
        marker="o",
        markerfacecolor="none",
        markeredgecolor="black",
        markeredgewidth=0.8,
        markersize=4.5,
    )
    axes[0, 0].plot(x1, glmdiag["res"], **point)
    axes[0, 0].set_xlabel("Linear predictor")
    axes[0, 0].set_ylabel("Residuals")

    y2 = np.asarray(glmdiag["rd"], dtype=np.float64)
    order = _rank_average(y2)
    quantiles = _qnorm(_ppoints(len(y2)))
    # R drops the fractional part of an average rank when it indexes with it.
    x2 = quantiles[np.trunc(order).astype(int) - 1]
    axes[0, 1].plot(x2, y2, **point)
    axes[0, 1].axline((0.0, 0.0), slope=1.0, linestyle="--", color="black")
    axes[0, 1].set_xlabel("Ordered deviance residuals")
    axes[0, 1].set_ylabel("Quantiles of standard normal")

    hh = glmdiag["h"] / (1.0 - glmdiag["h"])
    cook = np.asarray(glmdiag["cook"], dtype=np.float64)
    axes[1, 0].plot(hh, cook, **point)
    axes[1, 0].set_xlabel("h/(1-h)")
    axes[1, 0].set_ylabel("Cook statistic")
    rx = (float(np.min(hh)), float(np.max(hh)))
    ry = (float(np.min(cook)), float(np.max(cook)))
    rank = int(glmfit.rank)
    n_obs = rank + int(glmfit.df_residual)
    cooky = 8.0 / (n_obs - 2.0 * rank)
    hy = (2.0 * rank) / (n_obs - 2.0 * rank)
    if ry[0] <= cooky <= ry[1]:
        axes[1, 0].axhline(cooky, linestyle="--", color="black")
    if rx[0] <= hy <= rx[1]:
        axes[1, 0].axvline(hy, linestyle="--", color="black")

    axes[1, 1].plot(cases, cook, **point)
    axes[1, 1].set_xlabel("Case")
    axes[1, 1].set_ylabel("Cook statistic")
    if ry[0] <= cooky <= ry[1]:
        axes[1, 1].axhline(cooky, linestyle="--", color="black")
    _fig.tight_layout()
    if ret:
        return glmdiag
    return None


def _adjust_k(n: int, k) -> int:
    if (k > n) or (k <= 1):
        raise ValueError("'K' outside allowable range")
    k_original = float(k)
    k_rounded = float(round(k_original))
    seen: set[int] = set()
    kvals: list[int] = []
    for divisor in range(1, n // 2 + 1):
        candidate = int(round(n / divisor))
        if candidate not in seen:
            seen.add(candidate)
            kvals.append(candidate)
    if int(k_rounded) not in kvals:
        distance = [abs(candidate - k_rounded) for candidate in kvals]
        nearest = min(distance)
        k_rounded = float(next(candidate for candidate, gap in zip(kvals, distance) if gap == nearest))
    if k_rounded != k_original:
        warnings.warn(f"'K' has been set to {k_rounded:.6f}", stacklevel=3)
    return int(k_rounded)


def _folds(n: int, k: int) -> np.ndarray:
    """``sample0(rep(1:K, ceiling(n/K)), n)`` with R's sample.int."""
    repeats = math.ceil(n / k)
    pool = np.tile(np.arange(1, k + 1), repeats)
    drawn = sample_int(len(pool), n, replace=False)
    return pool[np.asarray(drawn, dtype=int) - 1]


def predict(glmfit: GlmFit, newdata: dict | None = None, type: str = "link") -> np.ndarray:
    """Linear predictor, or the mean when ``type`` is ``"response"``."""
    if type not in {"link", "response"}:
        raise ValueError("type must be 'link' or 'response'")
    if newdata is None:
        eta = np.asarray(glmfit.linear_predictors, dtype=np.float64)
    else:
        _y, x, _names = _model_matrix(glmfit.formula, newdata)
        eta = x @ np.asarray(glmfit.coefficients, dtype=np.float64)
    if type == "link":
        return eta
    return _linkinv(glmfit.family, eta)


def _mse(y, yhat) -> float:
    y = _as_float(y)
    yhat = _as_float(yhat)
    return float(np.mean((y - yhat) ** 2))


def cv_glm(data: dict, glmfit: GlmFit, cost=None, K=None) -> dict:
    """K-fold cross-validation prediction error for a gaussian or binomial fit.

    The default cost is the mean squared error. ``K`` defaults to the number of
    rows, which is leave-one-out. Groups are the same draw as R when
    ``boot.rng.set_seed`` was called first: ``sample0(rep(1:K, ceiling(n/K)), n)``.
    The returned ``delta`` is the raw estimate and the bias-adjusted estimate.
    """
    if cost is None:
        cost = _mse
    n = _nrow(data)
    if len(glmfit.y) != n:
        raise ValueError("glmfit was not fitted to this data")
    if K is None:
        K = n
    k = _adjust_k(n, K)
    groups = _folds(n, k)
    counts = np.bincount(groups, minlength=k + 1)
    y = np.asarray(glmfit.y, dtype=np.float64)
    cost_0 = float(cost(y, glmfit.fitted_values))
    raw = 0.0
    for group in range(1, int(np.max(groups)) + 1):
        hold_out = np.flatnonzero(groups == group)
        keep = np.flatnonzero(groups != group)
        refit = glm(
            glmfit.formula,
            _subset(data, keep),
            family=glmfit.family,
            weights=glmfit.prior_weights[keep],
        )
        share = float(counts[group]) / n
        raw += share * float(cost(y[hold_out], predict(refit, _subset(data, hold_out), type="response")))
        cost_0 -= share * float(cost(y, predict(refit, data, type="response")))
    delta = np.array([raw, raw + cost_0], dtype=np.float64)
    return {"K": k, "delta": delta}
