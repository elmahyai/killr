"""simEVV, simVEE, simEVE, and simVVE of mclust 6.1.3 (R/mclust2.R).

Each function follows the R function line for line. The result is an
n x (d + 1) ``SimMatrix``: column 0 is the component label, then the d draws
named ``1`` ... ``d``, as these R functions set their dimnames. The
missing-parameter branch warns and returns NA, as R does.

The factor for component k is ``t(orientation) * sss``, where ``sss`` is the
scale times the shape vector. In R, ``*`` on a matrix and a length-d vector
multiplies row i by ``sss[i]``, which is what ``factor.T * sss[:, None]`` does.
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

__all__ = ["simEVV", "simVEE", "simEVE", "simVVE"]


def _dnames(d: int) -> list[str]:
    return ["group"] + [str(j) for j in range(1, d + 1)]


def _missing(n: int, cols: int, model: str) -> SimMatrix:
    warnings.warn("parameters are missing", stacklevel=3)
    return SimMatrix(np.full((n, cols), np.nan), model)


def _shape_dg(shape: Any, d: int, G: int) -> np.ndarray:
    """R: ``sqrt(shape)``, made d x G when G == 1, then checked against (d, G)."""
    a = np.sqrt(np.asarray(shape, dtype=float))
    if G == 1 and a.ndim < 2:
        a = a.reshape(d, 1)
    if a.shape != (d, G):
        raise ValueError("shape incompatible with mean")
    return a


def _scale_scalar(scale: Any) -> float:
    a = np.sqrt(np.asarray(scale, dtype=float)).reshape(-1)
    if a.size != 1:
        raise ValueError("scale must be a single value for this model")
    return float(a[0])


def _scale_vector(scale: Any, G: int) -> np.ndarray:
    a = np.sqrt(np.asarray(scale, dtype=float)).reshape(-1)
    if a.size != G:
        raise ValueError("scale incompatible with mean")
    return a


def _shape_vector(shape: Any, d: int) -> np.ndarray:
    a = np.sqrt(np.asarray(shape, dtype=float)).reshape(-1)
    if a.size != d:
        raise ValueError("shape incompatible with mean")
    return a


def simEVV(parameters: dict[str, Any], n: int, seed: int | None = None, **_: Any) -> SimMatrix:
    """Simulate from the EVV model (equal volume, varying shape and orientation)."""
    seed_if_given(seed)
    mu = as_mean_matrix(parameters["mean"])
    d, G = mu.shape
    if is_missing_parameters(parameters):
        return _missing(n, d + 1, "EVV")
    clabels = sample_labels(G, n, pro_vector(parameters, G))
    variance = parameters["variance"]
    rtshape = _shape_dg(variance["shape"], d, G)
    rtscale = _scale_scalar(variance["scale"])
    orientation = np.asarray(variance["orientation"], dtype=float)

    def chol_for(k: int) -> np.ndarray:
        sss = rtscale * rtshape[:, k]
        return orientation[:, :, k].T * sss[:, None]

    x = draw_rows(mu, clabels, G, d, chol_for)
    return SimMatrix(labelled(clabels, x), "EVV", _dnames(d))


def simVEE(parameters: dict[str, Any], n: int, seed: int | None = None, **_: Any) -> SimMatrix:
    """Simulate from the VEE model (varying volume, equal shape and orientation)."""
    seed_if_given(seed)
    mu = as_mean_matrix(parameters["mean"])
    d, G = mu.shape
    if is_missing_parameters(parameters):
        return _missing(n, d + 1, "VEE")
    clabels = sample_labels(G, n, pro_vector(parameters, G))
    variance = parameters["variance"]
    rtshape = _shape_vector(variance["shape"], d)
    rtscale = _scale_vector(variance["scale"], G)
    orientation = np.asarray(variance["orientation"], dtype=float)

    def chol_for(k: int) -> np.ndarray:
        sss = rtscale[k] * rtshape
        return orientation.T * sss[:, None]

    x = draw_rows(mu, clabels, G, d, chol_for)
    return SimMatrix(labelled(clabels, x), "VEE", _dnames(d))


def simEVE(parameters: dict[str, Any], n: int, seed: int | None = None, **_: Any) -> SimMatrix:
    """Simulate from the EVE model (equal volume, varying shape, equal orientation)."""
    seed_if_given(seed)
    mu = as_mean_matrix(parameters["mean"])
    d, G = mu.shape
    if is_missing_parameters(parameters):
        return _missing(n, d + 1, "EVE")
    clabels = sample_labels(G, n, pro_vector(parameters, G))
    variance = parameters["variance"]
    rtshape = _shape_dg(variance["shape"], d, G)
    rtscale = _scale_scalar(variance["scale"])
    orientation = np.asarray(variance["orientation"], dtype=float)

    def chol_for(k: int) -> np.ndarray:
        sss = rtscale * rtshape[:, k]
        return orientation.T * sss[:, None]

    x = draw_rows(mu, clabels, G, d, chol_for)
    return SimMatrix(labelled(clabels, x), "EVE", _dnames(d))


def simVVE(parameters: dict[str, Any], n: int, seed: int | None = None, **_: Any) -> SimMatrix:
    """Simulate from the VVE model (varying volume and shape, equal orientation)."""
    seed_if_given(seed)
    mu = as_mean_matrix(parameters["mean"])
    d, G = mu.shape
    if is_missing_parameters(parameters):
        return _missing(n, d + 1, "VVE")
    clabels = sample_labels(G, n, pro_vector(parameters, G))
    variance = parameters["variance"]
    rtshape = _shape_dg(variance["shape"], d, G)
    rtscale = _scale_vector(variance["scale"], G)
    orientation = np.asarray(variance["orientation"], dtype=float)

    def chol_for(k: int) -> np.ndarray:
        sss = rtscale[k] * rtshape[:, k]
        return orientation.T * sss[:, None]

    x = draw_rows(mu, clabels, G, d, chol_for)
    return SimMatrix(labelled(clabels, x), "VVE", _dnames(d))
