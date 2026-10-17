"""Multivariate normal draws from MASS mvrnorm."""

from __future__ import annotations

import numpy as np

from mass._r_rng import norm_rand
from mass.errors import MassError


def _symmetric_eigen(sigma: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values, vectors = np.linalg.eigh(sigma)
    order = np.argsort(values)[::-1]
    return values[order], vectors[:, order]


def _center_columns(x: np.ndarray) -> np.ndarray:
    return x - x.mean(axis=0, keepdims=True)


def _scale_columns(x: np.ndarray) -> np.ndarray:
    n = x.shape[0]
    if n <= 1:
        scale = np.ones(x.shape[1], dtype=float)
    else:
        scale = np.std(x, axis=0, ddof=1)
    return x / scale


def mvrnorm(
    n: int = 1,
    mu=None,
    Sigma=None,
    tol: float = 1e-6,
    empirical: bool = False,
    EISPACK: bool = False,
):
    """Simulate from a multivariate normal, as MASS mvrnorm."""
    if mu is None or Sigma is None:
        raise TypeError("mvrnorm() missing required argument 'mu' or 'Sigma'")
    if EISPACK:
        raise MassError("'EISPACK' is no longer supported by R")
    mu_arr = np.asarray(mu, dtype=float).reshape(-1)
    sigma = np.asarray(Sigma, dtype=float)
    p = mu_arr.size
    if sigma.shape != (p, p):
        raise MassError("incompatible arguments")
    values, vectors = _symmetric_eigen(sigma)
    if values.size and not np.all(values >= -tol * abs(values[0])):
        raise MassError("'Sigma' is not positive definite")
    count = int(n)
    draws = np.fromiter((norm_rand() for _ in range(p * count)), dtype=float, count=p * count)
    x = draws.reshape(count, p, order="F")
    if empirical:
        x = _center_columns(x)
        _, _, vh = np.linalg.svd(x, full_matrices=True)
        x = x @ vh.T
        x = _scale_columns(x)
    root = np.sqrt(np.maximum(values, 0.0))
    x = mu_arr + (vectors @ (root[:, None] * x.T)).T
    if count == 1:
        return x.reshape(-1)
    return x
