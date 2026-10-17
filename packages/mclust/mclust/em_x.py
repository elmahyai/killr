"""One-component one-dimensional normal EM fit, ``emX`` (mclust 6.1.3).

R ``emX`` calls ``mvnX``, which calls the Fortran ``mvn1d`` routine. This
module calls the same routine through the ``mclust_kernels`` crate binding.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

import mclust_kernels

from mclust.mclust_options import mclust_options

__all__ = ["emX"]

# R: signif(.Machine$double.xmax, 6)
_XMAX = 1.797693e308


def emX(data, prior=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """Fit a one-component one-dimensional normal model."""
    if warn is None:
        warn = mclust_options("warn")
    x = np.asarray(data, dtype=float)
    if x.ndim > 2 or (x.ndim == 2 and x.shape[1] != 1):
        raise ValueError("data must be one dimensional")
    values = x.reshape(-1)
    n = int(values.size)
    if prior is not None:
        raise NotImplementedError("emX priors are not translated")

    out = mclust_kernels.mvn1d((values.tolist(), n, 0.0, 0.0, 0.0))
    mu = float(out[2])
    sigmasq = float(out[3])
    loglik = float(out[4])

    warning = None
    ret = 0
    if loglik > _XMAX:
        warning = "sigma-squared vanishes"
        if warn:
            warnings.warn(warning)
        loglik = float("nan")
        ret = -1

    variance = {"modelName": "X", "d": 1, "G": 1, "sigmasq": sigmasq}
    parameters = {"pro": 1.0, "mean": mu, "variance": variance}
    return {
        "modelName": "X",
        "prior": prior,
        "n": n,
        "d": 1,
        "G": 1,
        "parameters": parameters,
        "loglik": loglik,
        "WARNING": warning,
        "returnCode": ret,
    }
