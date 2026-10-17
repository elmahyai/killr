"""Translation of mclust ``estepEII``: E-step for the spherical equal-volume model."""

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


def estepEII(data: Any, parameters: dict[str, Any], warn: bool | None = None) -> dict[str, Any]:
    warn = warn_default(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]
    pro, K, vinv = mixing_setup(parameters, x, G)

    if has_missing_parameters(parameters):
        return missing_result("EII", n, p, G, K, parameters, warn)

    sigmasq = parameters["variance"].get("sigmasq")
    if sigmasq is None:
        raise ValueError("variance parameters are missing")
    sigsq = float(np.ravel(sigmasq)[0])
    if sigsq < 0:
        raise ValueError("sigma-squared is negative")
    if sigsq == 0:
        warning = "sigma-squared vanishes"
        if warn:
            warnings.warn(warning)
        z = np.full((n, K), np.nan)
        return result("EII", n, p, G, z, parameters, float("nan"), warning, -1)

    out = _k.eseii(
        (
            col_major(x),
            col_major(mu),
            sigsq,
            col_major(pro),
            n,
            p,
            G,
            vinv,
            0.0,
            [0.0] * (n * K),
        )
    )
    loglik = float(out[8])
    z = z_from_kernel(out[9], n, K)

    warning = None
    if loglik > DBL_MAX_SIGNIF:
        warning = "sigma-squared falls below threshold"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
        loglik = float("nan")
        ret = -1
    else:
        ret = 0
    return result("EII", n, p, G, z, parameters, loglik, warning, ret)
