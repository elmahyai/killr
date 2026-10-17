"""cdensEVV of mclust 6.1.3 (mclust2.R).

The R wrapper checks the arguments, then calls the Fortran kernel ``esevv`` from
``mclust_kernels`` with ``Gnoise = G`` and ``pro`` and ``Vinv`` set to -1. The kernel
returns every argument, so the outputs are read by position.
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

from mclust._cdens_common import (
    Cdens,
    col_major,
    from_kernel,
    has_na,
    na_result,
    orientation_arg,
    require,
    warn_default,
)
from mclust._estep_common import as_mean_matrix
from mclust_kernels import esevv

__all__ = ["cdensEVV"]

_EPS = sys.float_info.epsilon  # .Machine$double.eps
_MINUS_ONE = [-1.0]


def cdensEVV(
    data: Any,
    logarithm: bool = False,
    parameters: dict[str, Any] | None = None,
    warn: bool | None = None,
    **_: Any,
) -> Cdens:
    """Log (or plain) component densities for the EVV model (equal volume, variable shape and orientation)."""
    warn = warn_default(warn)
    if parameters is None:
        raise TypeError('argument "parameters" is missing, with no default')
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]
    if has_na(parameters, ("pro", "mean", "variance")):
        return na_result("EVV", n, G, logarithm, warn, "parameters are missing", 9)
    variance = parameters.get("variance") or {}
    require(variance, "scale", "shape", "orientation")
    # scale is one volume shared by all components, so only its first element is used.
    scale = float(np.ravel(variance["scale"])[0])
    shape = np.asarray(variance["shape"], dtype=float).reshape((p, G), order="F")
    out = esevv(
        (
            col_major(x),
            [0.0] * (n * G),
            n,
            p,
            G,
            G,
            col_major(mu),
            orientation_arg(variance["orientation"], p, G),
            scale,
            col_major(shape),
            _MINUS_ONE,
            -1.0,
            0.0,
            _EPS,
        )
    )
    return from_kernel("EVV", n, G, logarithm, out[1], float(out[12]), warn, "singular covariance")
