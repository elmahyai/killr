"""Heteroscedasticity-consistent covariances."""

from __future__ import annotations

import warnings

import numpy as np

from .estfun import bread, estfun, nobs0, sandwich
from .model import Fit, match_arg


_TYPES = ["HC3", "const", "HC", "HC0", "HC1", "HC2", "HC4", "HC4m", "HC5"]


def _omega_function(type_name: str):
    if type_name == "const":
        return lambda residuals, diaghat, df: np.ones(len(residuals)) * np.sum(residuals ** 2) / df
    if type_name == "HC0":
        return lambda residuals, diaghat, df: residuals ** 2
    if type_name == "HC1":
        return lambda residuals, diaghat, df: residuals ** 2 * len(residuals) / df
    if type_name == "HC2":
        return lambda residuals, diaghat, df: residuals ** 2 / (1 - diaghat)
    if type_name == "HC3":
        return lambda residuals, diaghat, df: residuals ** 2 / (1 - diaghat) ** 2
    if type_name == "HC4":
        def omega(residuals, diaghat, df):
            n = len(residuals)
            p = int(round(float(np.sum(diaghat))))
            delta = np.minimum(4, n * diaghat / p)
            return residuals ** 2 / (1 - diaghat) ** delta
        return omega
    if type_name == "HC4m":
        def omega(residuals, diaghat, df):
            gamma = (1.0, 1.5)
            n = len(residuals)
            p = int(round(float(np.sum(diaghat))))
            delta = np.minimum(gamma[0], n * diaghat / p) + np.minimum(gamma[1], n * diaghat / p)
            return residuals ** 2 / (1 - diaghat) ** delta
        return omega
    def omega(residuals, diaghat, df):
        k = 0.7
        n = len(residuals)
        p = int(round(float(np.sum(diaghat))))
        delta = np.minimum(n * diaghat / p, np.maximum(4, n * k * np.max(diaghat) / p))
        return residuals ** 2 / np.sqrt((1 - diaghat) ** delta)
    return omega


def _working_residuals(fit: Fit, scores: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = scores / fit.x
    residuals = np.nanmean(ratio, axis=1)
    all0 = np.all(np.abs(scores) < np.finfo(float).eps, axis=1)
    residuals[all0] = 0.0
    return residuals, all0


def meatHC(x: Fit, type="HC3", omega=None, **_kwargs) -> np.ndarray:
    type_name = match_arg(type, _TYPES)
    if type_name == "HC":
        type_name = "HC0"
    design = x.x
    n = design.shape[0]
    df = n - design.shape[1]
    diaghat = x.hatvalues()
    scores = np.asarray(estfun(x), dtype=float)
    residuals, all0 = _working_residuals(x, scores)
    if np.any(all0) and type_name == "const":
        if x.klass[0] == "glm":
            residuals = np.asarray(x.working_residuals, dtype=float) * np.asarray(x.working_weights, dtype=float)
            if x.family not in {"poisson", "binomial"} or not getattr(x, "fixed_dispersion", True):
                residuals = residuals * np.sum(x.working_weights) / np.sum(residuals ** 2)
        elif x.klass[0] == "lm":
            residuals = np.asarray(x.residuals, dtype=float)
            if x.prior_weights is not None:
                residuals = residuals * x.prior_weights
    if omega is None:
        omega = _omega_function(type_name)
        if type_name != "const":
            limit = 1 - math_sqrt_eps()
            if type_name in {"HC0", "HC1"}:
                close = diaghat > limit
            else:
                close = diaghat > limit
            if np.any(close):
                which = np.flatnonzero(close) + 1
                shown = [str(item) for item in which[:10]]
                if len(which) > 10:
                    shown.append("...")
                warnings.warn(
                    f"{type_name} covariances are numerically unstable for hat values close to 1 "
                    f"as for observation(s) {', '.join(shown)}",
                    RuntimeWarning,
                    stacklevel=2,
                )
    if callable(omega):
        omega = omega(residuals, diaghat, df)
    scaled = np.sqrt(omega)[:, None] * design
    return (scaled.T @ scaled) / n


def math_sqrt_eps() -> float:
    return float(np.sqrt(np.finfo(float).eps))


def vcovHC_default(x: Fit, type="HC3", omega=None, sandwich_=True, **kwargs) -> np.ndarray:
    meat = meatHC(x, type=type, omega=omega)
    if sandwich_:
        return sandwich(x, meat_=meat, **kwargs)
    return meat


def vcovHC_mlm(x: Fit, type="HC3", omega=None, sandwich_=True, **kwargs) -> np.ndarray:
    type_name = match_arg(type, _TYPES)
    if type_name == "HC":
        type_name = "HC0"
    design = x.x
    n = design.shape[0]
    df = n - design.shape[1]
    diaghat = x.hatvalues()
    residuals = np.asarray(x.residuals, dtype=float)
    if omega is None:
        if type_name == "const":
            warnings.warn("not implemented for 'mlm' objects, using vcov() instead", RuntimeWarning, stacklevel=2)
            sigma = (residuals.T @ residuals) / df
            return np.kron(sigma, np.linalg.inv(design.T @ design))
        omega = _omega_function(type_name)
    omega_values = np.column_stack([omega(residuals[:, i], diaghat, df) for i in range(residuals.shape[1])])
    blocks = []
    for i in range(omega_values.shape[1]):
        scale = np.sign(residuals[:, i]) * np.sqrt(omega_values[:, i])
        blocks.append(scale[:, None] * design)
    stacked = np.column_stack(blocks)
    meat = (stacked.T @ stacked) / n
    if sandwich_:
        return sandwich(x, meat_=meat, **kwargs)
    return meat


def vcovHC(x: Fit, type="HC3", omega=None, sandwich_=True, **kwargs) -> np.ndarray:
    if x.klass[0] == "mlm":
        return vcovHC_mlm(x, type=type, omega=omega, sandwich_=sandwich_, **kwargs)
    return vcovHC_default(x, type=type, omega=omega, sandwich_=sandwich_, **kwargs)
