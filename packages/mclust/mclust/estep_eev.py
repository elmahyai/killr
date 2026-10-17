"""Translation of mclust ``estepEEV``: E-step for the ellipsoidal equal-volume-shape model."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

import mclust_kernels as _k
from mclust._estep_common import (
    DBL_MAX_SIGNIF,
    as_mean_matrix,
    col_major,
    has_missing_parameters,
    missing_result,
    mixing_setup,
    result,
    warn_default,
    z_from_kernel,
)


def estepEEV(data: Any, parameters: dict[str, Any], warn: bool | None = None) -> dict[str, Any]:
    warn = warn_default(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]
    pro, K, vinv = mixing_setup(parameters, x, G)

    if has_missing_parameters(parameters):
        return missing_result("EEV", n, p, G, K, parameters, warn)

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
            col_major(pro),
            n,
            p,
            G,
            vinv,
            [0.0] * p,
            [0.0] * p,
            0.0,
            [0.0] * (n * K),
        )
    )
    loglik = float(out[12])
    z = z_from_kernel(out[13], n, K)

    warning = None
    if loglik > DBL_MAX_SIGNIF:
        warning = "singular covariance"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
        loglik = float("nan")
        ret = -1
    else:
        ret = 0
    return result("EEV", n, p, G, z, parameters, loglik, warning, ret)
