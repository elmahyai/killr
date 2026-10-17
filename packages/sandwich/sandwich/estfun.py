"""Bread, meat, and the estimating functions."""

from __future__ import annotations

import numpy as np

from .model import Fit, SandwichError
from .series import Zoo, is_zoo, zoo


def _as_fit(x) -> Fit:
    if not isinstance(x, Fit):
        raise SandwichError("x must be a fitted model")
    return x


def nobs0(x) -> int:
    if isinstance(x, Fit):
        return x.nobs
    if isinstance(x, np.ndarray):
        return int(x.shape[0])
    raise SandwichError("nobs() could not be computed")


def estfun(x, **_kwargs) -> np.ndarray:
    fit = _as_fit(x)
    kind = fit.klass[0]
    if kind == "lm":
        value = _estfun_lm(fit)
    elif kind == "mlm":
        value = _estfun_mlm(fit)
    elif kind == "glm":
        value = _estfun_glm(fit)
    elif kind == "nls":
        value = np.asarray(fit.residuals, dtype=float)[:, None] * np.asarray(fit.gradient, dtype=float)
    elif kind == "rlm":
        psi = fit.psi(np.asarray(fit.residuals, dtype=float) / fit.scale)
        weights = 1.0 if fit.prior_weights is None else fit.prior_weights
        value = np.asarray(psi, dtype=float)[:, None] * weights * fit.x
    elif kind in {"polr", "clm", "coxph", "survreg", "hurdle", "zeroinfl", "mlogit", "multinom", "gam"}:
        value = _estfun_extra(fit)
    else:
        raise SandwichError(f"estfun() is not implemented for class '{kind}'")
    if kind == "lm":
        value = _restore_index(value, fit.residuals if not is_zoo(fit.residuals) else fit.residuals)
    return value


def _restore_index(value, residuals):
    if is_zoo(residuals):
        return zoo(value, residuals.index, residuals.frequency)
    return value


def _estfun_lm(fit: Fit) -> np.ndarray:
    weights = 1.0 if fit.prior_weights is None else fit.prior_weights[:, None]
    return np.asarray(fit.residuals, dtype=float)[:, None] * weights * fit.x


def _estfun_mlm(fit: Fit) -> np.ndarray:
    weights = 1.0 if fit.prior_weights is None else fit.prior_weights[:, None]
    blocks = []
    names = []
    responses = fit.response_names or [str(i + 1) for i in range(fit.residuals.shape[1])]
    for i, response in enumerate(responses):
        block = np.asarray(fit.residuals[:, i], dtype=float)[:, None] * weights * fit.x
        blocks.append(block)
        names.extend(f"{response}:{name}" for name in fit.coef_names)
    value = np.column_stack(blocks)
    value = _drop_aliased(value, fit)
    return value


def _drop_aliased(value, fit: Fit):
    return value


def _dispersion(fit: Fit) -> float:
    family = fit.family or ""
    if family in {"poisson", "binomial"} and getattr(fit, "fixed_dispersion", True):
        return 1.0
    working = np.asarray(fit.working_residuals, dtype=float) * np.asarray(fit.working_weights, dtype=float)
    return float(np.sum(working ** 2) / np.sum(fit.working_weights))


def _estfun_glm(fit: Fit) -> np.ndarray:
    working = np.asarray(fit.working_residuals, dtype=float) * np.asarray(fit.working_weights, dtype=float)
    return working[:, None] * fit.x / _dispersion(fit)


def _estfun_extra(fit: Fit) -> np.ndarray:
    if fit.klass[0] == "mlogit":
        return np.asarray(fit.gradient, dtype=float)
    if fit.klass[0] == "coxph":
        weights = 1.0 if fit.prior_weights is None else fit.prior_weights[:, None]
        return weights * np.asarray(fit.score_residuals, dtype=float)
    if fit.klass[0] == "survreg":
        weights = 1.0 if fit.prior_weights is None else fit.prior_weights[:, None]
        gradient = np.asarray(fit.residuals_dg, dtype=float)[:, None] * weights * fit.x
        if getattr(fit, "residuals_ds", None) is not None:
            gradient = np.column_stack([gradient, fit.residuals_ds])
        return gradient
    if hasattr(fit, "scores"):
        return np.asarray(fit.scores, dtype=float)
    raise SandwichError(f"estfun() is not implemented for class '{fit.klass[0]}'")


def _bread_matrix(fit: Fit) -> np.ndarray:
    weights = None
    if fit.klass[0] == "glm":
        weights = np.asarray(fit.working_weights, dtype=float)
    elif fit.prior_weights is not None and fit.klass[0] == "lm":
        weights = np.asarray(fit.prior_weights, dtype=float)
    gram = fit.x.T @ fit.x if weights is None else fit.x.T @ (weights[:, None] * fit.x)
    return np.linalg.inv(gram)


def bread(x, **_kwargs) -> np.ndarray:
    fit = _as_fit(x)
    kind = fit.klass[0]
    if kind == "lm":
        return _bread_matrix(fit) * fit.nobs
    if kind == "glm":
        return _bread_matrix(fit) * fit.nobs * _dispersion(fit)
    if kind == "mlm":
        base = _bread_matrix(fit) * fit.nobs
        width = fit.coefficients.shape[1]
        return np.kron(np.eye(width), base)
    if kind == "nls":
        return _bread_matrix(fit) * fit.nobs
    if kind in {"polr", "clm", "hurdle", "zeroinfl"}:
        return np.asarray(fit.vcov, dtype=float) * fit.nobs
    if kind == "survreg":
        return fit.nobs * np.asarray(fit.vcov, dtype=float)
    if kind == "coxph":
        return fit.nobs * np.asarray(fit.vcov, dtype=float)
    if kind == "gam":
        return np.asarray(fit.cov_unscaled_matrix, dtype=float) * fit.nobs
    if kind == "mlogit":
        return np.asarray(fit.vcov, dtype=float) * len(np.asarray(fit.residuals))
    if kind == "rlm":
        deriv = fit.psi(np.asarray(fit.residuals, dtype=float) / fit.scale, deriv=1)
        weights = 1.0 if fit.prior_weights is None else fit.prior_weights
        scaled = np.sqrt(np.abs(deriv / fit.scale))[:, None] * weights * fit.x
        gram = scaled.T @ scaled
        return np.linalg.inv(gram) * fit.nobs
    if hasattr(fit, "vcov"):
        return fit.nobs * np.asarray(fit.vcov, dtype=float)
    raise SandwichError(f"bread() is not implemented for class '{kind}'")


def meat(x, adjust: bool = False, **_kwargs) -> np.ndarray:
    scores = estfun(x)
    if is_zoo(scores):
        scores = np.asarray(scores.data, dtype=float)
    scores = np.asarray(scores, dtype=float)
    n = scores.shape[0]
    k = scores.shape[1]
    value = scores.T @ scores / n
    if adjust:
        value = n / (n - k) * value
    return value


def sandwich(x, bread_=None, meat_=None, **kwargs) -> np.ndarray:
    bread_matrix = bread(x) if bread_ is None else (bread_(x) if callable(bread_) else np.asarray(bread_, dtype=float))
    meat_matrix = meat(x, **kwargs) if meat_ is None else (meat_(x, **kwargs) if callable(meat_) else np.asarray(meat_, dtype=float))
    n = nobs0(x) if not isinstance(x, Fit) else estfun(x).shape[0]
    if is_zoo(estfun(x)):
        n = estfun(x).data.shape[0]
    return (1.0 / n) * bread_matrix @ meat_matrix @ bread_matrix


def vcovOPG(x, adjust: bool = False, **_kwargs) -> np.ndarray:
    scores = np.asarray(estfun(x), dtype=float)
    n = scores.shape[0]
    k = scores.shape[1]
    _q, r = np.linalg.qr(scores, mode="reduced")
    value = np.linalg.inv(r.T @ r)
    if adjust:
        value = n / (n - k) * value
    return value
