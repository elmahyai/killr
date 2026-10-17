"""E-step for the EVV covariance model of mclust 6.1.3 (mclust2.R).

The density is computed by the Fortran kernel ``esevv`` in the
``mclust_kernels`` crate. The kernel takes the orientation as ``aperm(O)``
and every array in column-major order, as R's ``.Fortran`` call does.
"""

from __future__ import annotations

import math
import sys
import warnings
from typing import Any

import numpy as np

from mclust.hypvol import hypvol
from mclust.mclust_options import mclust_options
from mclust_kernels import esevv

__all__ = ["estepEVV"]

# R: signif(.Machine$double.xmax, 6)
_LOGLIK_LIMIT = float("%.6g" % sys.float_info.max)
# R: .Machine$double.eps
_EPS = sys.float_info.epsilon


def _numeric_leaves(value: Any):
    """Yield the numbers inside a value, as R's unlist would."""
    if value is None or isinstance(value, str):
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _numeric_leaves(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _numeric_leaves(item)
    else:
        arr = np.asarray(value)
        if arr.dtype.kind in "biuf":
            for item in arr.ravel(order="F"):
                yield float(item)


def _has_missing(parameters: dict[str, Any], keys: tuple[str, ...]) -> bool:
    """R: any(is.na(unlist(parameters[keys]))). Missing entries drop out, as in unlist."""
    return any(math.isnan(v) for v in _numeric_leaves([parameters.get(k) for k in keys]))


def _col(a: Any) -> list[float]:
    """Column-major values, as R's as.double() gives."""
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def _call(kernel: Any, *args: Any) -> list[Any]:
    """The binding takes one tuple holding the Fortran arguments in order."""
    return kernel(args)


def _warn_flag(warn: bool | None) -> bool:
    return bool(mclust_options("warn")) if warn is None else bool(warn)


def _variance(parameters: dict[str, Any]) -> dict[str, Any]:
    return parameters.get("variance") or {}


def _require(variance: dict[str, Any], *keys: str) -> None:
    if any(variance.get(k) is None for k in keys):
        raise ValueError("variance parameters are missing")


def _proportions(parameters: dict[str, Any]) -> np.ndarray:
    pro = np.asarray(parameters["pro"], dtype=float)
    return pro / pro.sum()


def _noise(pro: np.ndarray, G: int, x: np.ndarray, parameters: dict[str, Any]):
    """Return the number of columns K of z and Vinv (None without a noise component)."""
    if pro.size == G + 1:
        vinv = parameters.get("Vinv")
        vinv = None if vinv is None else float(np.ravel(vinv)[0])
        if vinv is None or vinv <= 0:
            vinv = hypvol(x, reciprocal=True)
        return G + 1, float(vinv)
    if pro.size != G:
        raise ValueError("pro improperly specified")
    return G, None


def _vinv_arg(vinv: float | None) -> float:
    """R: as.double(if (is.null(Vinv)) -1 else Vinv)."""
    return -1.0 if vinv is None else float(vinv)


def _orientation_arg(orientation: Any, p: int, G: int) -> list[float]:
    """R: as.double(aperm(O, c(2, 1, 3)))."""
    o = np.asarray(orientation, dtype=float).reshape((p, p, G), order="F")
    return _col(np.transpose(o, (1, 0, 2)))


def _result(model, n, d, G, z, parameters, loglik, warning, code) -> dict[str, Any]:
    return {
        "modelName": model,
        "n": n,
        "d": d,
        "G": G,
        "z": z,
        "parameters": parameters,
        "loglik": loglik,
        "WARNING": warning,
        "returnCode": code,
    }


def _fail(model, n, d, G, K, parameters, warn, message, code) -> dict[str, Any]:
    """The R branches that return NA for z and loglik and a warning."""
    if warn:
        warnings.warn(message)
    return _result(
        model, n, d, G, np.full((n, K), np.nan), parameters, float("nan"), message, code
    )


def estepEVV(data: Any, parameters: dict[str, Any], warn: bool | None = None, **_: Any) -> dict[str, Any]:
    """E-step for the EVV model (equal volume, variable shape and orientation)."""
    warn = _warn_flag(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    n, p = x.shape
    pro = _proportions(parameters)
    mu = np.asarray(parameters["mean"], dtype=float)
    if mu.ndim == 1:
        mu = mu.reshape(-1, 1)
    G = mu.shape[1]
    K, vinv = _noise(pro, G, x, parameters)
    if _has_missing(parameters, ("pro", "mean", "variance")):
        return _fail("EVV", n, p, G, K, parameters, warn, "parameters are missing", 9)
    variance = _variance(parameters)
    _require(variance, "scale", "shape", "orientation")
    # scale is one volume shared by all components, so only its first element is used.
    scale = float(np.ravel(variance["scale"])[0])
    shape = np.asarray(variance["shape"], dtype=float).reshape((p, G), order="F")
    out = _call(esevv,
        _col(x),
        [0.0] * (n * K),
        n,
        p,
        G,
        K,
        _col(mu),
        _orientation_arg(variance["orientation"], p, G),
        scale,
        _col(shape),
        _col(pro),
        _vinv_arg(vinv),
        0.0,
        _EPS,
    )
    z_flat = out[1]
    loglik = float(out[12])
    if loglik > _LOGLIK_LIMIT:
        return _fail("EVV", n, p, G, K, parameters, warn, "singular covariance", -1)
    z = np.asarray(z_flat, dtype=float).reshape((n, K), order="F")
    return _result("EVV", n, p, G, z, parameters, loglik, None, 0)
