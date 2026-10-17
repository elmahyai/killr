"""Translation of mclust ``estepE``: E-step for the one-dimensional equal-variance model."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

import mclust_kernels as _k
from mclust._estep_common import (
    DBL_MAX_SIGNIF,
    col_major,
    has_missing_parameters,
    missing_result,
    mixing_setup,
    result,
    warn_default,
    z_from_kernel,
)


def estepE(data: Any, parameters: dict[str, Any], warn: bool | None = None) -> dict[str, Any]:
    warn = warn_default(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim > 2 or (x.ndim == 2 and x.shape[1] != 1):
        raise ValueError("data must be one-dimensional")
    x = x.reshape(-1)
    n = x.size
    mu = np.asarray(parameters["mean"], dtype=float).reshape(-1)
    G = mu.size
    pro, K, vinv = mixing_setup(parameters, x, G)

    if has_missing_parameters(parameters):
        return missing_result("E", n, 1, G, K, parameters, warn)

    variance = parameters["variance"]
    sigmasq = variance.get("sigmasq")
    if sigmasq is None:
        raise ValueError("variance parameters are missing")
    if np.size(sigmasq) > 1 and warn:
        warnings.warn("more than one sigma-squared specified")
    sigsq = float(np.ravel(sigmasq)[0])
    if sigsq < 0:
        raise ValueError("sigma-squared is negative")
    if sigsq == 0:
        warning = "sigma-squared vanishes"
        if warn:
            warnings.warn(warning)
        z = np.full((n, K), np.nan)
        return result("E", n, 1, G, z, parameters, float("nan"), warning, -1)

    out = _k.es1e(
        (
            col_major(x),
            col_major(mu),
            sigsq,
            col_major(pro),
            n,
            G,
            vinv,
            0.0,
            [0.0] * (n * K),
        )
    )
    loglik = float(out[7])
    z = z_from_kernel(out[8], n, K)

    warning = None
    if loglik > DBL_MAX_SIGNIF:
        warning = "cannot compute E-step"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
        loglik = float("nan")
        ret = -1
    else:
        ret = 0
    return result("E", n, 1, G, z, parameters, loglik, warning, ret)
