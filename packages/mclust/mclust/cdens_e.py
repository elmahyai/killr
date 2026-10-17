"""Translation of mclust ``cdensE``: component log densities for the univariate equal-variance model."""

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


def cdensE(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> dict[str, Any]:
    warn = warn_default(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim > 2 or (x.ndim == 2 and x.shape[1] != 1):
        raise ValueError("data must be one-dimensional")
    x = x.reshape(-1)
    n = x.size
    mu = np.asarray(parameters["mean"], dtype=float).reshape(-1)
    G = mu.size

    if has_missing(parameters, ("mean", "variance")):
        return missing_cdens("E", n, G, logarithm, warn, "parameters are missing")

    sigmasq = parameters["variance"].get("sigmasq")
    if sigmasq is None:
        raise ValueError("variance parameters are missing")
    if np.size(sigmasq) > 1 and warn:
        warnings.warn("more than one sigma-squared given")
    sigsq = float(np.ravel(sigmasq)[0])
    if sigsq < 0:
        raise ValueError("sigma-squared is negative")
    if sigsq == 0:
        return missing_cdens("E", n, G, logarithm, warn, "sigma-squared vanishes")

    # R passes pro = -1 (a length-one vector in R); the kernel returns unnormalised log densities.
    out = _k.es1e(
        (
            col_major(x),
            col_major(mu),
            sigsq,
            [-1.0] * G,
            n,
            G,
            -1.0,
            0.0,
            [0.0] * (n * G),
        )
    )
    loglik = float(out[7])
    z = z_from_kernel(out[8], n, G)

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
    return cdens_result("E", z, logarithm, warning, ret)
