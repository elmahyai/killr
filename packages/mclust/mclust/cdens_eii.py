"""Translation of mclust ``cdensEII``: component log densities for the spherical equal-volume model."""

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


def cdensEII(
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
        return missing_cdens("EII", n, G, logarithm, warn, "parameters are missing")

    sigmasq = parameters["variance"].get("sigmasq")
    if sigmasq is None:
        raise ValueError("sigma-squared is missing")
    sigsq = float(np.ravel(sigmasq)[0])
    if sigsq < 0:
        raise ValueError("sigma-squared is negative")
    if sigsq == 0:
        return missing_cdens("EII", n, G, logarithm, warn, "sigma-squared vanishes")

    out = _k.eseii(
        (
            col_major(x),
            col_major(mu),
            sigsq,
            [-1.0] * G,
            n,
            p,
            G,
            -1.0,
            0.0,
            [0.0] * (n * G),
        )
    )
    loglik = float(out[8])
    z = z_from_kernel(out[9], n, G)

    warning = None
    if loglik > DBL_MAX_SIGNIF:
        warning = "sigma-squared falls below threshold"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
        ret = -1
    else:
        if not logarithm:
            z = np.exp(z)
        ret = 0
    return cdens_result("EII", z, logarithm, warning, ret)
