"""Translation of mclust ``cdensEEE``: component log densities for the ellipsoidal equal-shape-and-volume model.

The Fortran kernel ``eseee`` comes from the ``cvmclustda`` crate (crates/cvmclustda).
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np

from mclust._cdens_gauss import (
    DBL_MAX_SIGNIF,
    cdens_result,
    has_missing,
    missing_cdens,
    warn_default,
)
from mclust._estep_common import as_mean_matrix

try:
    from cvmclustda import eseee
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "cvmclustda"))
    from cvmclustda import eseee


def _f64(a: Any) -> np.ndarray:
    return np.asfortranarray(np.asarray(a, dtype=float))


def cdensEEE(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> dict[str, Any]:
    # R's cdensEEE has no warn default line; Python applies mclust.options("warn") when warn is None.
    warn = warn_default(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)  # R: as.matrix(data)
    if x.ndim != 2:
        raise ValueError("data must be a matrix or a vector")
    x = _f64(x)
    n, p = x.shape
    mu = _f64(as_mean_matrix(parameters["mean"]))
    G = mu.shape[1]

    if has_missing(parameters, ("pro", "mean", "variance")):
        return missing_cdens("EEE", n, G, logarithm, warn, "parameters are missing")

    chol_sigma = parameters["variance"].get("cholSigma")
    if chol_sigma is None:
        raise ValueError("variance parameters are missing")
    chol = _f64(chol_sigma)

    # R passes pro = -1; the kernel needs one entry per component to size its output.
    pro = np.full(G, -1.0)
    lapack_info, loglik, z_flat, n_i, k_i = eseee(True, x, mu, chol, pro, -1.0)
    z = np.asarray(z_flat, dtype=float).reshape(int(n_i), int(k_i), order="F")

    warning = None
    lap = int(lapack_info)
    if lap != 0:
        if lap > 0:
            warning = "sigma is not positive definite"
        else:
            warning = "input error for LAPACK DPOTRF"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
        ret = -9
    elif loglik > DBL_MAX_SIGNIF:
        warning = "singular covariance"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
        ret = -1
    else:
        if not logarithm:
            z = np.exp(z)
        ret = 0
    return cdens_result("EEE", z, logarithm, warning, ret)
