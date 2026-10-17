"""Single-component diagonal multivariate normal EM fit, ``emXXI`` (mclust 6.1.3).

R ``emXXI`` calls ``mvnXXI``, which calls the Fortran ``mvnxxi`` routine. This
module calls the same routine through the ``mclust_kernels`` crate binding.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

import mclust_kernels

from mclust.mclust_options import mclust_options

__all__ = ["emXXI"]

# R: signif(.Machine$double.xmax, 6)
_XMAX = 1.797693e308


def _as_matrix(data) -> np.ndarray:
    x = np.asarray(data, dtype=float)
    if x.ndim < 2 or x.shape[1] == 1:
        raise ValueError("for multidimensional data only")
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    return x


def emXXI(data, prior=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """Fit a one-component diagonal multivariate normal model."""
    if warn is None:
        warn = mclust_options("warn")
    x = _as_matrix(data)
    n, p = x.shape
    if prior is not None:
        raise NotImplementedError("emXXI priors are not translated")

    out = mclust_kernels.mvnxxi(
        (x.ravel(order="F").tolist(), n, p, [0.0] * p, 0.0, [0.0] * p, 0.0)
    )
    mu = np.asarray(out[3], dtype=float)
    scale = float(out[4])
    shape = np.asarray(out[5], dtype=float)
    loglik = float(out[6])

    warning = None
    ret = 0
    if loglik > _XMAX:
        warning = "singular covariance"
        if warn:
            warnings.warn(warning)
        loglik = float("nan")
        ret = -1

    sigma = np.diag(scale * shape)
    variance = {
        "modelName": "XXI",
        "d": p,
        "G": 1,
        "Sigma": sigma,
        "sigma": sigma.reshape(p, p, 1),
        "scale": scale,
        "shape": shape,
    }
    parameters = {"pro": 1.0, "mean": mu.reshape(p, 1), "variance": variance}
    return {
        "modelName": "XXI",
        "prior": prior,
        "n": n,
        "d": p,
        "G": 1,
        "parameters": parameters,
        "loglik": loglik,
        "WARNING": warning,
        "returnCode": ret,
    }
