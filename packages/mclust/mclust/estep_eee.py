"""Translation of mclust ``estepEEE``: E-step for the ellipsoidal equal-volume-shape-orientation model."""

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


def estepEEE(data: Any, parameters: dict[str, Any], warn: bool | None = None) -> dict[str, Any]:
    warn = warn_default(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix or a vector")
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]
    pro, K, vinv = mixing_setup(parameters, x, G)

    if has_missing_parameters(parameters):
        return missing_result("EEE", n, p, G, K, parameters, warn)

    chol = parameters["variance"].get("cholSigma")
    if chol is None:
        raise ValueError("variance parameters are missing")

    # The kernel writes the LAPACK Cholesky status into the work array, w[0].
    out = _k.eseee(
        (
            1,
            col_major(x),
            col_major(mu),
            col_major(chol),
            col_major(pro),
            n,
            p,
            G,
            vinv,
            [0.0] * p,
            0.0,
            [0.0] * (n * K),
        )
    )
    lapack_info = int(out[9][0])
    loglik = float(out[10])
    z = z_from_kernel(out[11], n, K)

    warning = None
    if lapack_info != 0:
        if lapack_info > 0:
            warning = "sigma is not positive definite"
            ret = -4
        else:
            warning = "input error for LAPACK DPOTRF"
            ret = -5
        warnings.warn(warning)
        z[:] = np.nan
        loglik = float("nan")
    elif loglik > DBL_MAX_SIGNIF:
        warning = "singular covariance"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
        loglik = float("nan")
        ret = -1
    else:
        ret = 0
    return result("EEE", n, p, G, z, parameters, loglik, warning, ret)
