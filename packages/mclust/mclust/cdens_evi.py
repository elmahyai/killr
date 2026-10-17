"""Translation of mclust ``cdensEVI``: component log densities for the diagonal equal-volume model with varying shape."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

import mclust_kernels as _k
from mclust._cdens_gauss import (
    DBL_MAX_SIGNIF,
    cdens_result,
    col_major,
    has_missing,
    missing_cdens,
    warn_default,
    z_from_kernel,
)
from mclust._estep_common import as_mean_matrix


def cdensEVI(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> dict[str, Any]:
    warn = warn_default(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]

    if has_missing(parameters, ("pro", "mean", "variance")):
        return missing_cdens("EVI", n, G, logarithm, warn, "parameters are missing")

    variance = parameters["variance"]
    scale = variance.get("scale")
    shape = variance.get("shape")
    if scale is None or shape is None:
        raise ValueError("variance parameters are missing")

    out = _k.esevi(
        (
            col_major(x),
            col_major(mu),
            float(np.ravel(scale)[0]),
            col_major(shape),
            [-1.0] * G,
            n,
            p,
            G,
            -1.0,
            0.0,
            [0.0] * (n * G),
        )
    )
    loglik = float(out[9])
    z = z_from_kernel(out[10], n, G)

    warning = None
    if loglik > DBL_MAX_SIGNIF:
        warning = "singular covariance"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
        ret = -1
    else:
        if not logarithm:
            z = np.exp(z)
        ret = 0
    return cdens_result("EVI", z, logarithm, warning, ret)
