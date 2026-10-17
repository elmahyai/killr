"""E-step for the VEE, EVE, and VVE covariance models of mclust 6.1.3 (mclust2.R).

The density is computed by the Fortran kernels ``esvee``, ``eseve``, and
``esvve`` in the ``mclust_kernels`` crate. The kernels take the orientation
as ``t(O)`` and the vectors and matrices in column-major order, as R's
``.Fortran`` calls do.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np

from mclust.hypvol import hypvol
from mclust.mclust_options import mclust_options
from mclust_kernels import esvee, eseve, esvve

__all__ = ["estep_vee", "estep_eve", "estep_vve"]

_EPS = float(np.finfo(float).eps)
# R: signif(.Machine$double.xmax, 6)
_LOGLIK_LIMIT = float("%.6g" % float(np.finfo(float).max))


def _numeric_leaves(value: Any):
    """Yield the numbers inside a parameter value, as R's unlist would."""
    if value is None or isinstance(value, str):
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _numeric_leaves(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _numeric_leaves(item)
        return
    arr = np.asarray(value)
    if arr.dtype.kind in "biuf":
        for item in arr.ravel(order="F"):
            yield float(item)


def _has_missing(parameters: dict[str, Any]) -> bool:
    values = [parameters.get(key) for key in ("pro", "mean", "variance")]
    return any(math.isnan(v) for v in _numeric_leaves(values))


def _estep(
    model_name: str,
    kernel: Any,
    data: Any,
    parameters: dict[str, Any],
    warn: bool | None,
    scale_is_scalar: bool,
) -> dict[str, Any]:
    if warn is None:
        warn = bool(mclust_options("warn"))
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    n, p = x.shape
    pro = np.asarray(parameters["pro"], dtype=float)
    pro = pro / pro.sum()
    l = pro.size
    mu = np.asarray(parameters["mean"], dtype=float)
    if mu.ndim == 1:
        mu = mu.reshape(-1, 1)
    G = mu.shape[1]
    noise = l == G + 1
    if not noise:
        if l != G:
            raise ValueError("pro improperly specified")
        K = G
        vinv = None
    else:
        K = G + 1
        vinv = parameters.get("Vinv")
        if vinv is None or vinv <= 0:
            vinv = hypvol(x, reciprocal=True)

    if _has_missing(parameters):
        warning = "parameters are missing"
        if warn:
            warnings.warn(warning)
        return {
            "modelName": model_name,
            "n": n,
            "d": p,
            "G": G,
            "z": np.full((n, K), np.nan),
            "parameters": parameters,
            "loglik": float("nan"),
            "WARNING": warning,
            "returnCode": 9,
        }

    variance = parameters.get("variance") or {}
    if (
        variance.get("scale") is None
        or variance.get("shape") is None
        or variance.get("orientation") is None
    ):
        raise ValueError("variance parameters are missing")

    scale = np.asarray(variance["scale"], dtype=float)
    shape = np.asarray(variance["shape"], dtype=float)
    orientation = np.asarray(variance["orientation"], dtype=float)

    x_flat = x.ravel(order="F").tolist()
    mu_flat = mu.ravel(order="F").tolist()
    # R passes as.double(t(O)); t(O) in column-major order is O in row-major order.
    o_flat = orientation.ravel(order="C").tolist()
    if scale_is_scalar:
        scale_arg: Any = float(scale.ravel()[0])
    else:
        scale_arg = scale.ravel(order="F").tolist()
    shape_arg = shape.ravel(order="F").tolist()
    pro_flat = pro.ravel(order="F").tolist()
    vinv_arg = -1.0 if vinv is None else float(vinv)

    z_init = [0.0] * (n * K)
    # The crate's pyfunctions take one tuple of the 14 Fortran arguments.
    out = kernel(
        (
            x_flat,
            z_init,
            n,
            p,
            G,
            K,
            mu_flat,
            o_flat,
            scale_arg,
            shape_arg,
            pro_flat,
            vinv_arg,
            0.0,
            _EPS,
        )
    )
    z = np.asarray(out[1], dtype=float).reshape((n, K), order="F")
    loglik = float(out[12])

    warning = None
    if loglik > _LOGLIK_LIMIT:
        warning = "cannot compute E-step"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
        loglik = float("nan")
        ret = -1
    else:
        ret = 0
    return {
        "modelName": model_name,
        "n": n,
        "d": p,
        "G": G,
        "z": z,
        "parameters": parameters,
        "loglik": loglik,
        "WARNING": warning,
        "returnCode": ret,
    }


def estep_vee(data: Any, parameters: dict[str, Any], warn: bool | None = None) -> dict[str, Any]:
    """E-step for the VEE model (equal shape and orientation, variable volume)."""
    return _estep(
        "VEE",
        esvee,
        data,
        parameters,
        warn,
        scale_is_scalar=False,
    )


def estep_eve(data: Any, parameters: dict[str, Any], warn: bool | None = None) -> dict[str, Any]:
    """E-step for the EVE model (equal volume and orientation, variable shape)."""
    return _estep(
        "EVE",
        eseve,
        data,
        parameters,
        warn,
        scale_is_scalar=True,
    )


def estep_vve(data: Any, parameters: dict[str, Any], warn: bool | None = None) -> dict[str, Any]:
    """E-step for the VVE model (equal orientation, variable volume and shape)."""
    return _estep(
        "VVE",
        esvve,
        data,
        parameters,
        warn,
        scale_is_scalar=False,
    )
