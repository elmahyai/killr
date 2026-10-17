"""Translation of mclust ``cdensEEV``: component log densities for the ellipsoidal equal-volume-shape model."""

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


def cdensEEV(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> dict[str, Any]:
    # R's cdensEEV has no warn default line; Python applies mclust.options("warn") when warn is None.
    warn = warn_default(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]

    if has_missing(parameters, ("pro", "mean", "variance")):
        return missing_cdens("EEV", n, G, logarithm, warn, "parameters are missing")

    variance = parameters["variance"]
    scale = variance.get("scale")
    shape = variance.get("shape")
    orientation = variance.get("orientation")
    if scale is None or shape is None or orientation is None:
        raise ValueError("variance parameters are missing")

    # R: aperm(orientation, c(2, 1, 3)) before the call.
    o_t = np.transpose(np.asarray(orientation, dtype=float), (1, 0, 2))

    out = _k.eseev(
        (
            col_major(x),
            col_major(mu),
            float(np.ravel(scale)[0]),
            col_major(shape),
            col_major(o_t),
            [-1.0] * G,
            n,
            p,
            G,
            -1.0,
            [0.0] * p,
            [0.0] * p,
            0.0,
            [0.0] * (n * G),
        )
    )
    loglik = float(out[12])
    z = z_from_kernel(out[13], n, G)

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
    return cdens_result("EEV", z, logarithm, warning, ret)
