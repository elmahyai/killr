"""Negative binomial GLM with theta estimation (MASS ``glm.nb``)."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from mass.addterm import _model_matrix
from mass.errors import MassError

_DBL_EPS = float(np.finfo(np.float64).eps)
_THETA_EPS = _DBL_EPS**0.25


@dataclass
class GlmControl:
    maxit: int = 25
    epsilon: float = 1e-8
    trace: int = 0


def _as_link_name(link: Any) -> str:
    if isinstance(link, str):
        name = link
    elif callable(link) and getattr(link, "__name__", None):
        name = link.__name__
    else:
        name = str(link)
    if name not in {"log", "identity", "sqrt"}:
        raise MassError(
            f'"{name}" link not available for negative binomial family; '
            'available links are "identity", "log" and "sqrt"'
        )
    return name


@dataclass
class _Link:
    name: str

    def linkfun(self, mu: np.ndarray) -> np.ndarray:
        mu = np.asarray(mu, dtype=float)
        if self.name == "log":
            return np.log(np.clip(mu, _DBL_EPS, None))
        if self.name == "sqrt":
            return np.sqrt(np.clip(mu, 0.0, None))
        return mu.copy()

    def linkinv(self, eta: np.ndarray) -> np.ndarray:
        eta = np.asarray(eta, dtype=float)
        if self.name == "log":
            out = np.exp(eta)
            limit = np.log(np.finfo(float).max) - 1.0
            out[eta > limit] = np.finfo(float).max
            return out
        if self.name == "sqrt":
            return eta**2
        return eta.copy()

    def mu_eta(self, eta: np.ndarray) -> np.ndarray:
        eta = np.asarray(eta, dtype=float)
        if self.name == "log":
            mu = self.linkinv(eta)
            return np.clip(mu, _DBL_EPS, None)
        if self.name == "sqrt":
            return 2.0 * eta
        return np.ones_like(eta, dtype=float)

    def valideta(self, eta: np.ndarray) -> bool:
        eta = np.asarray(eta, dtype=float)
        if self.name == "sqrt":
            return bool(np.all(np.isfinite(eta)))
        return bool(np.all(np.isfinite(eta)))


def _logmdigamma_asymptotic(z: float) -> float:
    x = 1.0 / (z * z)
    tail = x * (
        -1.0 / 12.0
        + x
        * (
            1.0 / 120.0
            + x
            * (
                -1.0 / 252.0
                + x
                * (
                    1.0 / 240.0
                    + x
                    * (
                        -1.0 / 132.0
                        + x * (691.0 / 32760.0 + (x * (-1.0 / 12.0 + (3617.0 * x) / 8160.0)))
                    )
                )
            )
        )
    )
    return 1.0 / (2.0 * z) - tail


def _logmdigamma(z: float) -> float:
    if z <= 0 or math.isnan(z):
        return math.nan
    if z < 5.0:
        return (
            math.log(z / (z + 5.0))
            + _logmdigamma(z + 5.0)
            + 1.0 / z
            + 1.0 / (z + 1.0)
            + 1.0 / (z + 2.0)
            + 1.0 / (z + 3.0)
            + 1.0 / (z + 4.0)
        )
    return _logmdigamma_asymptotic(z)


def _digamma_scalar(x: float) -> float:
    if x <= 0:
        return math.nan
    return math.log(x) - _logmdigamma(x)


def _trigamma_scalar(x: float) -> float:
    if x <= 0:
        return math.nan
    step = max(x * 1e-5, 1e-8)
    return (_digamma_scalar(x + step) - _digamma_scalar(x - step)) / (2.0 * step)


def _digamma(values: np.ndarray) -> np.ndarray:
    flat = np.asarray(values, dtype=float).reshape(-1)
    out = np.array([_digamma_scalar(float(v)) for v in flat], dtype=float)
    return out.reshape(np.asarray(values).shape)


def _trigamma(values: np.ndarray) -> np.ndarray:
    flat = np.asarray(values, dtype=float).reshape(-1)
    out = np.array([_trigamma_scalar(float(v)) for v in flat], dtype=float)
    return out.reshape(np.asarray(values).shape)


_QR_TOL = 1e-11


def _qr_coef_glm(x: np.ndarray, z: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, int]:
    design = x * w[:, None]
    n_coef = design.shape[1]
    if n_coef == 0:
        return np.zeros(0), 0
    q_factor, r_factor = np.linalg.qr(design, mode="reduced")
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
    return beta, rank


def _nb_deviance(y: np.ndarray, mu: np.ndarray, wt: np.ndarray, theta: float) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    mu = np.clip(np.asarray(mu, dtype=float), _DBL_EPS, None)
    wt = np.asarray(wt, dtype=float)
    y_num = np.where(y > 0, y * np.log(np.maximum(1.0, y) / mu), 0.0)
    terms = wt * (y_num - (y + theta) * np.log((y + theta) / (mu + theta)))
    return 2.0 * np.asarray(terms, dtype=np.longdouble)


def _poisson_deviance(y: np.ndarray, mu: np.ndarray, wt: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    mu = np.clip(np.asarray(mu, dtype=float), _DBL_EPS, None)
    wt = np.asarray(wt, dtype=float)
    term = np.zeros_like(y)
    pos = y > 0
    term[pos] = y[pos] * np.log(y[pos] / mu[pos])
    return 2.0 * wt * (term - (y - mu))


def _gammaln(values: np.ndarray) -> np.ndarray:
    flat = np.asarray(values, dtype=float).reshape(-1)
    out = np.array([math.lgamma(float(v)) for v in flat], dtype=float)
    return out.reshape(np.asarray(values).shape)


def _loglik_nb(n: int, th: float, mu: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    mu = np.asarray(mu, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.asarray(w, dtype=float)
    y0 = y == 0
    log_mu = np.zeros_like(y)
    log_mu[~y0] = np.log(mu[~y0])
    log_mu[y0] = 0.0
    pieces = (
        _gammaln(th + y)
        - math.lgamma(th)
        - _gammaln(y + 1.0)
        + th * math.log(th)
        + y * log_mu
        - (th + y) * np.log(th + mu)
    )
    flat = (w * pieces).reshape(-1)
    return math.fsum(float(v) for v in flat)


def _theta_ml(
    y: np.ndarray,
    mu: np.ndarray,
    weights: np.ndarray,
    *,
    limit: int = 10,
    eps: float = _THETA_EPS,
    trace: bool = False,
) -> tuple[float, float | None, str | None]:
    y = np.asarray(y, dtype=float)
    mu = np.clip(np.asarray(mu, dtype=float), _DBL_EPS, None)
    weights = np.asarray(weights, dtype=float)
    n = float(np.sum(weights))
    t0 = n / float(np.sum(weights * (y / mu - 1.0) ** 2))
    it = 0
    del_val = 1.0
    info_val = 0.0
    warn_msg: str | None = None
    if trace:
        pass
    while it + 1 < limit and abs(del_val) > eps:
        it += 1
        t0 = abs(t0)
        th = t0
        score = float(
            np.sum(
                weights
                * (
                    _digamma(th + y)
                    - _digamma(np.full_like(y, th))
                    + math.log(th)
                    + 1.0
                    - np.log(th + mu)
                    - (y + th) / (mu + th)
                )
            )
        )
        info_val = float(
            np.sum(
                weights
                * (
                    -_trigamma(th + y)
                    + _trigamma(np.full_like(y, th))
                    - 1.0 / th
                    + 2.0 / (mu + th)
                    - (y + th) / (mu + th) ** 2
                )
            )
        )
        del_val = score / info_val
        t0 = t0 + del_val
    if t0 < 0:
        t0 = 0.0
        warn_msg = "estimate truncated at zero"
        warnings.warn(warn_msg, stacklevel=3)
    if it == limit:
        warn_msg = "iteration limit reached"
        warnings.warn(warn_msg, stacklevel=3)
    se = math.sqrt(1.0 / info_val) if info_val != 0.0 else math.nan
    return float(t0), se, warn_msg


@dataclass
class _Family:
    name: str
    link: _Link
    theta: float | None = None

    def variance(self, mu: np.ndarray) -> np.ndarray:
        mu = np.asarray(mu, dtype=float)
        if self.name == "poisson":
            return mu
        th = self.theta
        assert th is not None
        return mu + mu**2 / th

    def dev_resids(self, y: np.ndarray, mu: np.ndarray, wt: np.ndarray) -> np.ndarray:
        if self.name == "poisson":
            return _poisson_deviance(y, mu, wt)
        assert self.theta is not None
        return _nb_deviance(y, mu, wt, self.theta)

    def validmu(self, mu: np.ndarray) -> bool:
        return bool(np.all(np.asarray(mu, dtype=float) > 0))


def _glm_fit(
    x: np.ndarray,
    y: np.ndarray,
    family: _Family,
    *,
    weights: np.ndarray,
    offset: np.ndarray | None = None,
    start: np.ndarray | None = None,
    etastart: np.ndarray | None = None,
    mustart: np.ndarray | None = None,
    intercept: bool = True,
    maxit: int = 25,
    epsilon: float = 1e-8,
    trace: bool = False,
) -> dict[str, Any]:
    n, p = x.shape
    prior = np.asarray(weights, dtype=float)
    off = np.zeros(n) if offset is None else np.asarray(offset, dtype=float)
    link = family.link
    if mustart is not None:
        mu = np.asarray(mustart, dtype=float)
        eta = link.linkfun(mu)
    elif etastart is not None:
        eta = np.asarray(etastart, dtype=float)
        mu = link.linkinv(eta)
    elif start is not None:
        beta = np.asarray(start, dtype=float)
        eta = x @ beta + off
        mu = link.linkinv(eta)
    else:
        if family.name == "poisson":
            mu = y + (y == 0) / 6.0
        else:
            mu = y + (y == 0) / 6.0
        mu = np.clip(mu, _DBL_EPS, None)
        eta = link.linkfun(mu)
    dev_old = float(np.sum(family.dev_resids(y, mu, prior)))
    beta = np.zeros(p)
    if start is not None and etastart is None and mustart is None:
        beta = np.asarray(start, dtype=float)
    rank = 0
    for iteration in range(maxit):
        mu = np.clip(mu, _DBL_EPS, None)
        mu_eta = link.mu_eta(eta)
        variance = family.variance(mu)
        good = (
            (prior > 0)
            & (mu > 0)
            & (mu_eta != 0)
            & np.isfinite(variance)
            & (variance > 0)
        )
        if not np.any(good):
            break
        working = (y[good] - mu[good]) / mu_eta[good]
        z = eta[good] - off[good] + working
        w_sq = prior[good] * mu_eta[good] ** 2 / variance[good]
        scale = np.sqrt(w_sq)
        beta, rank = _qr_coef_glm(x[good], z, scale)
        eta = x @ beta + off
        mu = link.linkinv(eta)
        dev = float(np.sum(family.dev_resids(y, mu, prior), dtype=np.longdouble))
        if trace:
            pass
        if abs(dev - dev_old) / (0.1 + abs(dev)) < epsilon:
            dev_old = dev
            break
        dev_old = dev
    mu = link.linkinv(eta)
    dev = float(np.sum(family.dev_resids(y, mu, prior), dtype=np.longdouble))
    n_ok = int(np.sum(prior > 0))
    df_res = n_ok - rank
    with np.errstate(divide="ignore", invalid="ignore"):
        residuals = (y - mu) / link.mu_eta(eta)
    return {
        "coefficients": beta,
        "fitted_values": mu,
        "linear_predictors": eta,
        "deviance": dev,
        "df_residual": df_res,
        "rank": rank,
        "residuals": residuals,
        "prior_weights": prior,
    }


@dataclass
class NegbinFit:
    """Fitted ``glm.nb`` model (class ``negbin`` in R)."""

    coefficients: np.ndarray
    fitted_values: np.ndarray
    theta: float
    se_theta: float
    twologlik: float
    deviance: float
    df_residual: int
    rank: int
    formula: str
    terms: Any = None
    call: dict[str, Any] = field(default_factory=dict)
    prior_weights: np.ndarray | None = None
    offset: np.ndarray | None = None
    y: np.ndarray | None = None
    model: Any = None
    th_warn: str | None = None
    aic: float | None = None
    control: GlmControl | None = None
    method: str = "glm.fit"


def glm_nb(
    formula: str,
    data: dict,
    *,
    weights=None,
    start=None,
    etastart=None,
    mustart=None,
    offset=None,
    control: GlmControl | None = None,
    init_theta=None,
    link="log",
    model: bool = True,
    x: bool = False,
    y_ret: bool = True,
) -> NegbinFit:
    """Fit a negative binomial GLM with ML estimate of ``theta``."""
    if control is None:
        control = GlmControl()
    link_name = _as_link_name(link)
    link_obj = _Link(link_name)
    x_mat, y, names, _labels = _model_matrix(data, formula)
    n = y.shape[0]
    w = np.ones(n, dtype=float) if weights is None else np.asarray(weights, dtype=float)
    if np.any(w < 0):
        raise MassError("negative weights not allowed")
    off = None if offset is None else np.asarray(offset, dtype=float)
    intercept = "(Intercept)" in names

    if init_theta is None:
        fam0 = _Family("poisson", link_obj)
    else:
        fam0 = _Family("negative.binomial", link_obj, theta=float(init_theta))

    fit = _glm_fit(
        x_mat,
        y,
        fam0,
        weights=w,
        offset=off,
        start=None if start is None else np.asarray(start, dtype=float),
        etastart=None if etastart is None else np.asarray(etastart, dtype=float),
        mustart=None if mustart is None else np.asarray(mustart, dtype=float),
        intercept=intercept,
        maxit=control.maxit,
        epsilon=control.epsilon,
        trace=control.trace > 1,
    )
    mu = fit["fitted_values"]
    th, se_th, th_warn = _theta_ml(
        y,
        mu,
        w,
        limit=control.maxit,
        trace=control.trace > 2,
    )
    fam = _Family("negative.binomial", link_obj, theta=th)
    iter_count = 0
    d1 = math.sqrt(2 * max(1, fit["df_residual"]))
    d2 = 1.0
    del_theta = 1.0
    lm = _loglik_nb(n, th, mu, y, w)
    lm0 = lm + 2 * d1
    th_warn_final = th_warn
    while iter_count + 1 <= control.maxit and (abs(lm0 - lm) / d1 + abs(del_theta) / d2) > control.epsilon:
        iter_count += 1
        eta = link_obj.linkfun(mu)
        fit = _glm_fit(
            x_mat,
            y,
            fam,
            weights=w,
            offset=off,
            etastart=eta,
            intercept=intercept,
            maxit=control.maxit,
            epsilon=control.epsilon,
            trace=control.trace > 1,
        )
        t0 = th
        th, se_th, th_warn = _theta_ml(
            y,
            fit["fitted_values"],
            w,
            limit=control.maxit,
            trace=control.trace > 2,
        )
        if th_warn is not None:
            th_warn_final = th_warn
        fam = _Family("negative.binomial", link_obj, theta=th)
        mu = fit["fitted_values"]
        del_theta = t0 - th
        lm0 = lm
        lm = _loglik_nb(n, th, mu, y, w)
    # MASS keeps deviance from the prior glm.fit pass when one more coef update remains.
    saved_dev = fit["deviance"]
    if iter_count > 0 and iter_count < control.maxit:
        eta = link_obj.linkfun(mu)
        fit = _glm_fit(
            x_mat,
            y,
            fam,
            weights=w,
            offset=off,
            etastart=eta,
            intercept=intercept,
            maxit=control.maxit,
            epsilon=control.epsilon,
            trace=control.trace > 1,
        )
        th, se_th, th_warn = _theta_ml(
            y,
            fit["fitted_values"],
            w,
            limit=control.maxit,
            trace=control.trace > 2,
        )
        if th_warn is not None:
            th_warn_final = th_warn
        fam = _Family("negative.binomial", link_obj, theta=th)
        mu = fit["fitted_values"]
        lm = _loglik_nb(n, th, mu, y, w)
        fit["deviance"] = saved_dev
    if iter_count > control.maxit:
        warnings.warn("alternation limit reached", stacklevel=2)
        th_warn_final = "alternation limit reached"

    if off is not None and intercept and x_mat.shape[1] > 0:
        intercept_col = x_mat[:, [0]]
        null_fit = _glm_fit(
            intercept_col,
            y,
            fam,
            weights=w,
            offset=off,
            intercept=True,
            maxit=control.maxit,
            epsilon=control.epsilon,
        )
        fit["null_deviance"] = null_fit["deviance"]

    coef = fit["coefficients"]
    twologlik = 2.0 * lm
    aic = -twologlik + 2 * fit["rank"] + 2
    call = {
        "formula": formula,
        "init_theta": float(f"{th:.10g}"),
        "link": link_name,
    }
    out = NegbinFit(
        coefficients=coef,
        fitted_values=mu,
        theta=th,
        se_theta=se_th if se_th is not None else math.nan,
        twologlik=twologlik,
        deviance=fit["deviance"],
        df_residual=fit["df_residual"],
        rank=fit["rank"],
        formula=formula,
        call=call,
        prior_weights=w,
        offset=off,
        y=y if y_ret else None,
        th_warn=th_warn_final,
        aic=aic,
        control=control,
    )
    if model:
        out.model = {"y": y, "names": names}
    if x:
        out.x = x_mat  # type: ignore[attr-defined]
    return out
