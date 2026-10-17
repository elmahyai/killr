"""Gamma shape and dispersion helpers (MASS ``gamma.dispersion``)."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

import numpy as np

from mass.addterm import _model_matrix, _qr_coef


def _digamma_scalar(x: float) -> float:
    if x <= 0.0:
        return math.nan
    result = 0.0
    while x < 8.0:
        result -= 1.0 / x
        x += 1.0
    inv = 1.0 / x
    inv2 = inv * inv
    inv4 = inv2 * inv2
    result += math.log(x) - 0.5 * inv
    result -= inv2 * ((1.0 / 12.0) - inv2 * ((1.0 / 120.0) - inv2 * (1.0 / 252.0)))
    return result


def _trigamma_scalar(x: float) -> float:
    if x <= 0.0:
        return math.nan
    step = 1e-5 * max(1.0, x)
    return (_digamma_scalar(x + step) - _digamma_scalar(x - step)) / (2.0 * step)


def _gamma_deviance(y: np.ndarray, mu: np.ndarray) -> float:
    """Residual deviance stored on R ``glm`` fits with ``family = Gamma``."""
    mu = np.clip(mu, 1e-300, None)
    y = np.asarray(y, dtype=float)
    resid = np.sign(y - mu) * np.sqrt(np.maximum(0.0, 2.0 * ((y - mu) / mu - np.log(y / mu))))
    return float(np.sum(resid**2))


def _gamma_glm_fit(
    x: np.ndarray,
    y: np.ndarray,
    *,
    weights: np.ndarray | None = None,
    maxit: int = 25,
    epsilon: float = 1e-8,
) -> tuple[np.ndarray, np.ndarray, float, int, np.ndarray]:
    """Fit a Gamma GLM with inverse link, matching R ``glm(..., family = Gamma)``."""
    n = x.shape[0]
    prior = np.ones(n) if weights is None else np.asarray(weights, dtype=float)
    mu = np.clip(y, 1e-12, None)
    coef = np.zeros(x.shape[1])
    dev = math.inf
    for _ in range(maxit):
        mu = np.clip(mu, 1e-12, None)
        mu_eta = -(mu**2)
        variance = mu**2
        working_weights = prior * (mu_eta**2) / variance
        working = (y - mu) / mu_eta
        eta = 1.0 / mu
        z = eta + working
        scale = np.sqrt(working_weights)
        coef, rank = _qr_coef(x * scale[:, None], z * scale)
        eta = x @ coef
        mu = 1.0 / np.clip(eta, 1e-12, None)
        dev_new = _gamma_deviance(y, mu)
        if abs(dev - dev_new) / (0.1 + abs(dev_new)) < epsilon:
            dev = dev_new
            break
        dev = dev_new
    mu = np.clip(mu, 1e-12, None)
    mu_eta = -(mu**2)
    variance = mu**2
    working_weights = prior * (mu_eta**2) / variance
    working = (y - mu) / mu_eta
    eta = 1.0 / mu
    z = eta + working
    scale = np.sqrt(working_weights)
    _, rank = _qr_coef(x * scale[:, None], z * scale)
    return coef, mu, dev, rank, prior


@dataclass
class GammaGlmFit:
    """Minimal Gamma glm object for ``gamma.dispersion``."""

    y: np.ndarray
    fitted_values: np.ndarray
    prior_weights: np.ndarray
    deviance: float
    df_residual: int


def gamma_glm(formula: str, data: dict, *, weights=None) -> GammaGlmFit:
    """Fit ``formula`` with R's default Gamma family (inverse link)."""
    x, y, _names, _labels = _model_matrix(data, formula)
    prior = None if weights is None else np.asarray(weights, dtype=float)
    _coef, mu, dev, rank, prior_w = _gamma_glm_fit(x, y, weights=prior)
    n = y.shape[0]
    return GammaGlmFit(
        y=y,
        fitted_values=mu,
        prior_weights=prior_w,
        deviance=dev,
        df_residual=n - rank,
    )


def _gamma_shape_glm(
    object,
    *,
    it_lim: int = 10,
    eps_max: float | None = None,
    verbose: bool = False,
) -> tuple[float, float]:
    if eps_max is None:
        eps_max = float(np.finfo(float).eps**0.25)
    y = np.asarray(object.y, dtype=float)
    fitted = np.asarray(object.fitted_values, dtype=float)
    prior = object.prior_weights
    if prior is None:
        a = np.ones(y.shape[0], dtype=float)
    else:
        a = np.asarray(prior, dtype=float)
    u = fitted
    dbar = float(object.deviance) / float(object.df_residual)
    alpha = (6.0 + 2.0 * dbar) / (dbar * (6.0 + dbar))
    if verbose:
        print(f"Initial estimate: {alpha}")
    fixed = -y / u - np.log(u) + np.log(a) + 1.0 + np.log(y + (y == 0.0))
    eps = 1.0
    itr = 0
    inf = 0.0
    while abs(eps) > eps_max and (itr := itr + 1) <= it_lim:
        aa = a * alpha
        sc = float(np.sum(a * (fixed + np.log(alpha) - np.array([_digamma_scalar(v) for v in aa]))))
        inf = float(
            np.sum(a * (a * np.array([_trigamma_scalar(v) for v in aa]) - 1.0 / alpha))
        )
        alpha = alpha + (eps := sc / inf)
        if verbose:
            print(f"Iter. {itr} Alpha: {alpha}")
    if itr > it_lim:
        warnings.warn("iteration limit reached", stacklevel=2)
    se = math.sqrt(1.0 / inf)
    return alpha, se


def gamma_dispersion(object, /, **kwargs) -> float:
    """Reciprocal of the MLE shape parameter (MASS ``gamma.dispersion``)."""
    alpha, _se = _gamma_shape_glm(object, **kwargs)
    return 1.0 / alpha
