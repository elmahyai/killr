"""simVEV, simVII, simVVI, and simVVV of mclust 6.1.3 (R/mclust.R).

Each function follows the R function line for line: set the seed, check the
parameters, draw the labels, then draw each component. The result is an
n x (d + 1) ``SimMatrix``: column 0 is ``group``, then the d draws named
``x1`` ... ``xd``, as R's dimnames. simVII returns n x d when the parameters are
missing, as R does.

The random stream is R's (see ``mclust._sim_common``). The missing-parameter
branch warns "parameters are missing" and returns NA, as R does.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from mclust._sim_common import (
    SimMatrix,
    as_mean_matrix,
    draw_rows,
    is_missing_parameters,
    labelled,
    pro_vector,
    sample_labels,
    seed_if_given,
)

__all__ = ["simVEV", "simVII", "simVVI", "simVVV"]


def _xnames(d: int) -> list[str]:
    return ["group"] + [f"x{j}" for j in range(1, d + 1)]


def _missing(n: int, cols: int, model: str) -> SimMatrix:
    warnings.warn("parameters are missing", stacklevel=3)
    return SimMatrix(np.full((n, cols), np.nan), model)


def _chol_upper(sigma: np.ndarray) -> np.ndarray:
    """R ``chol``: the upper triangular U with t(U) %*% U = sigma."""
    return np.linalg.cholesky(np.asarray(sigma, dtype=float)).T


def simVEV(parameters: dict[str, Any], n: int, seed: int | None = None, **_: Any) -> SimMatrix:
    """Simulate from the VEV model (varying volume, equal shape, varying orientation)."""
    seed_if_given(seed)
    mu = as_mean_matrix(parameters["mean"])
    d, G = mu.shape
    if is_missing_parameters(parameters):
        return _missing(n, d + 1, "VEV")
    clabels = sample_labels(G, n, pro_vector(parameters, G))
    variance = parameters["variance"]
    rtshape = np.sqrt(np.asarray(variance["shape"], dtype=float)).reshape(-1)
    if rtshape.size != d:
        raise ValueError("shape incompatible with mean")
    rtscale = np.sqrt(np.asarray(variance["scale"], dtype=float)).reshape(-1)
    if rtscale.size != G:
        raise ValueError("scale incompatible with mean")
    orientation = np.asarray(variance["orientation"], dtype=float)

    def chol_for(k: int) -> np.ndarray:
        sss = rtscale[k] * rtshape
        return orientation[:, :, k].T * sss[:, None]

    x = draw_rows(mu, clabels, G, d, chol_for)
    return SimMatrix(labelled(clabels, x), "VEV", _xnames(d))


def simVII(parameters: dict[str, Any], n: int, seed: int | None = None, **_: Any) -> SimMatrix:
    """Simulate from the VII model (spherical, varying volume)."""
    seed_if_given(seed)
    mu = as_mean_matrix(parameters["mean"])
    d, G = mu.shape
    if is_missing_parameters(parameters):
        warnings.warn("parameters are missing", stacklevel=2)
        return SimMatrix(np.full((n, d), np.nan), "VII")
    clabels = sample_labels(G, n, pro_vector(parameters, G))
    sigmasq = np.asarray(parameters["variance"]["sigmasq"], dtype=float).reshape(-1)

    def chol_for(k: int) -> np.ndarray:
        return np.eye(d) * np.sqrt(sigmasq[k])  # R: diag(rep(sqrt(sigmasq[k]), d))

    x = draw_rows(mu, clabels, G, d, chol_for)
    return SimMatrix(labelled(clabels, x), "VII", _xnames(d))


def simVVI(parameters: dict[str, Any], n: int, seed: int | None = None, **_: Any) -> SimMatrix:
    """Simulate from the VVI model (diagonal, varying volume and shape)."""
    seed_if_given(seed)
    mu = as_mean_matrix(parameters["mean"])
    d, G = mu.shape
    if is_missing_parameters(parameters):
        return _missing(n, d + 1, "VVI")
    clabels = sample_labels(G, n, pro_vector(parameters, G))
    variance = parameters["variance"]
    shape = np.asarray(variance["shape"], dtype=float)
    if shape.shape != mu.shape:
        raise ValueError("shape incompatible with mean")
    rtshape = np.sqrt(shape)
    rtscale = np.sqrt(np.asarray(variance["scale"], dtype=float)).reshape(-1)
    if rtscale.size != G:
        raise ValueError("scale incompatible with mean")

    def chol_for(k: int) -> np.ndarray:
        return np.diag(rtscale[k] * rtshape[:, k])

    x = draw_rows(mu, clabels, G, d, chol_for)
    return SimMatrix(labelled(clabels, x), "VVI", _xnames(d))


def simVVV(parameters: dict[str, Any], n: int, seed: int | None = None, **_: Any) -> SimMatrix:
    """Simulate from the VVV model (unconstrained covariance, varying everything).

    R uses ``variance$cholsigma`` when it is given. Otherwise it uses
    ``variance$sigma`` and takes the Cholesky factor of each component.
    """
    seed_if_given(seed)
    mu = as_mean_matrix(parameters["mean"])
    d, G = mu.shape
    if is_missing_parameters(parameters):
        return _missing(n, d + 1, "VVV")
    clabels = sample_labels(G, n, pro_vector(parameters, G))
    variance = parameters["variance"]
    cholsigma = variance.get("cholsigma")
    if cholsigma is None:
        sigma = variance.get("sigma")
        if sigma is None:
            raise ValueError("variance parameters must include either sigma or cholsigma")
        sigma = np.asarray(sigma, dtype=float)
        cholsigma = np.stack([_chol_upper(sigma[:, :, k]) for k in range(sigma.shape[2])], axis=2)
    cholsigma = np.asarray(cholsigma, dtype=float)
    if cholsigma.ndim != 3 or cholsigma.shape[2] != G:
        raise ValueError("variance incompatible with mean")

    def chol_for(k: int) -> np.ndarray:
        return cholsigma[:, :, k]

    x = draw_rows(mu, clabels, G, d, chol_for)
    return SimMatrix(labelled(clabels, x), "VVV", _xnames(d))
