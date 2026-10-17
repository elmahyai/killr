"""E-step for the V, VEI, VEV, VII, VVI, and VVV models of mclust 6.1.3 (mclust.R).

Each function follows the R wrapper: it checks the arguments, adds the noise
component when there is one, and calls a Fortran kernel from the
``mclust_kernels`` crate (``es1v``, ``esvii``, ``esvei``, ``esvev``,
``esvvi``, ``esvvv``). Arrays go to the kernels in column-major order, as R's
``.Fortran`` calls do. The kernels return every argument, so the value needed
is picked by position.
"""

from __future__ import annotations

import math
import sys
import warnings
from typing import Any

import numpy as np

from mclust.hypvol import hypvol
from mclust.mclust_options import mclust_options
from mclust_kernels import es1v, esvei, esvev, esvii, esvvi, esvvv

__all__ = ["estepV", "estepVEI", "estepVEV", "estepVII", "estepVVI", "estepVVV"]

# R: signif(.Machine$double.xmax, 6)
_LOGLIK_LIMIT = float("%.6g" % sys.float_info.max)


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


def _mean_matrix(mean: Any) -> np.ndarray:
    """R: as.matrix(parameters$mean)."""
    mu = np.asarray(mean, dtype=float)
    return mu.reshape(-1, 1) if mu.ndim == 1 else mu


def _matrix_data(data: Any) -> np.ndarray:
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    return x


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


def _from_kernel(model, n, d, G, K, z_flat, loglik, parameters, warn, message):
    if loglik > _LOGLIK_LIMIT:
        return _fail(model, n, d, G, K, parameters, warn, message, -1)
    z = np.asarray(z_flat, dtype=float).reshape((n, K), order="F")
    return _result(model, n, d, G, z, parameters, loglik, None, 0)


def estepV(data: Any, parameters: dict[str, Any], warn: bool | None = None, **_: Any) -> dict[str, Any]:
    """E-step for the one-dimensional V model (variable variance per component)."""
    warn = _warn_flag(warn)
    x = np.asarray(data, dtype=float)
    if x.ndim > 2 or (x.ndim == 2 and x.shape[1] != 1):
        raise ValueError("data must be one-dimensional")
    x = x.reshape(-1)
    n = x.size
    pro = _proportions(parameters)
    mu = np.asarray(parameters["mean"], dtype=float).reshape(-1)
    G = mu.size
    K, vinv = _noise(pro, G, x, parameters)
    if _has_missing(parameters, ("pro", "mean", "variance")):
        return _fail("V", n, 1, G, K, parameters, warn, "parameters are missing", 9)
    sigmasq = _variance(parameters).get("sigmasq")
    if sigmasq is None:
        raise ValueError("variance parameters are missing")
    sig = np.asarray(sigmasq, dtype=float)
    if np.any(sig < 0):
        raise ValueError("sigma-squared is negative")
    if np.any(sig == 0):
        return _fail("V", n, 1, G, K, parameters, warn, "sigma-squared vanishes", -1)
    out = _call(es1v,
        _col(x), _col(mu), _col(sig), _col(pro), n, G, _vinv_arg(vinv), 0.0, [0.0] * (n * K)
    )
    return _from_kernel("V", n, 1, G, K, out[8], float(out[7]), parameters, warn, "cannot compute E-step")


def estepVII(data: Any, parameters: dict[str, Any], warn: bool | None = None, **_: Any) -> dict[str, Any]:
    """E-step for the VII model (spherical, variable volume)."""
    warn = _warn_flag(warn)
    x = _matrix_data(data)
    n, p = x.shape
    pro = _proportions(parameters)
    mu = _mean_matrix(parameters["mean"])
    G = mu.shape[1]
    K, vinv = _noise(pro, G, x, parameters)
    if _has_missing(parameters, ("pro", "mean", "variance")):
        return _fail("VII", n, p, G, K, parameters, warn, "parameters are missing", 9)
    sigmasq = _variance(parameters).get("sigmasq")
    if sigmasq is None:
        raise ValueError("variance parameters are missing")
    sig = np.asarray(sigmasq, dtype=float)
    if np.any(sig < 0):
        raise ValueError("sigma-squared is negative")
    if np.any(sig == 0):
        return _fail("VII", n, p, G, K, parameters, warn, "sigma-squared vanishes", -1)
    out = _call(esvii,
        _col(x), _col(mu), _col(sig), _col(pro), n, p, G, _vinv_arg(vinv), 0.0, [0.0] * (n * K)
    )
    return _from_kernel("VII", n, p, G, K, out[9], float(out[8]), parameters, warn, "cannot compute E-step")


def estepVEI(data: Any, parameters: dict[str, Any], warn: bool | None = None, **_: Any) -> dict[str, Any]:
    """E-step for the VEI model (diagonal, equal shape, variable volume)."""
    warn = _warn_flag(warn)
    x = _matrix_data(data)
    n, p = x.shape
    pro = _proportions(parameters)
    mu = _mean_matrix(parameters["mean"])
    G = mu.shape[1]
    K, vinv = _noise(pro, G, x, parameters)
    if _has_missing(parameters, ("pro", "mean", "variance")):
        return _fail("VEI", n, p, G, K, parameters, warn, "parameters are missing", 9)
    variance = _variance(parameters)
    _require(variance, "scale", "shape")
    out = _call(esvei,
        _col(x),
        _col(mu),
        _col(variance["scale"]),
        _col(variance["shape"]),
        _col(pro),
        n,
        p,
        G,
        _vinv_arg(vinv),
        0.0,
        [0.0] * (n * K),
    )
    return _from_kernel("VEI", n, p, G, K, out[10], float(out[9]), parameters, warn, "singular covariance")


def _orientation_arg(orientation: Any, p: int, G: int) -> list[float]:
    """R: as.double(aperm(O, c(2, 1, 3)))."""
    o = np.asarray(orientation, dtype=float).reshape((p, p, G), order="F")
    return _col(np.transpose(o, (1, 0, 2)))


def estepVEV(data: Any, parameters: dict[str, Any], warn: bool | None = None, **_: Any) -> dict[str, Any]:
    """E-step for the VEV model (equal shape, variable volume and orientation)."""
    warn = _warn_flag(warn)
    x = _matrix_data(data)
    n, p = x.shape
    pro = _proportions(parameters)
    mu = _mean_matrix(parameters["mean"])
    G = mu.shape[1]
    K, vinv = _noise(pro, G, x, parameters)
    if _has_missing(parameters, ("pro", "mean", "variance")):
        return _fail("VEV", n, p, G, K, parameters, warn, "parameters are missing", 9)
    variance = _variance(parameters)
    _require(variance, "scale", "shape", "orientation")
    out = _call(esvev,
        _col(x),
        _col(mu),
        _col(variance["scale"]),
        _col(variance["shape"]),
        _orientation_arg(variance["orientation"], p, G),
        _col(pro),
        n,
        p,
        G,
        _vinv_arg(vinv),
        [0.0] * p,
        [0.0] * p,
        0.0,
        [0.0] * (n * K),
    )
    return _from_kernel("VEV", n, p, G, K, out[13], float(out[12]), parameters, warn, "cannot compute E-step")


def estepVVI(data: Any, parameters: dict[str, Any], warn: bool | None = None, **_: Any) -> dict[str, Any]:
    """E-step for the VVI model (diagonal, variable volume and shape)."""
    warn = _warn_flag(warn)
    x = _matrix_data(data)
    n, p = x.shape
    pro = _proportions(parameters)
    mu = _mean_matrix(parameters["mean"])
    G = mu.shape[1]
    K, vinv = _noise(pro, G, x, parameters)
    # R checks the name "mu" here, which matches no element, so "mean" is not checked.
    if _has_missing(parameters, ("pro", "mu", "variance")):
        return _fail("VVI", n, p, G, K, parameters, warn, "parameters are missing", 9)
    variance = _variance(parameters)
    _require(variance, "scale", "shape")
    out = _call(esvvi,
        _col(x),
        _col(mu),
        _col(variance["scale"]),
        _col(variance["shape"]),
        _col(pro),
        n,
        p,
        G,
        _vinv_arg(vinv),
        0.0,
        [0.0] * (n * K),
    )
    return _from_kernel("VVI", n, p, G, K, out[10], float(out[9]), parameters, warn, "cannot compute E-step")


def estepVVV(data: Any, parameters: dict[str, Any], warn: bool | None = None, **_: Any) -> dict[str, Any]:
    """E-step for the VVV model (ellipsoidal, variable volume, shape, and orientation)."""
    warn = _warn_flag(warn)
    x = _matrix_data(data)
    n, p = x.shape
    pro = _proportions(parameters)
    mu = _mean_matrix(parameters["mean"])
    G = mu.shape[1]
    K, vinv = _noise(pro, G, x, parameters)
    if _has_missing(parameters, ("pro", "mean", "variance")):
        return _fail("VVV", n, p, G, K, parameters, warn, "parameters are missing", 9)
    variance = _variance(parameters)
    _require(variance, "cholsigma")
    chol = np.asarray(variance["cholsigma"], dtype=float).reshape((p, p, G), order="F")
    out = _call(esvvv,
        1,
        _col(x),
        _col(mu),
        _col(chol),
        _col(pro),
        n,
        p,
        G,
        _vinv_arg(vinv),
        [0.0] * p,
        0.0,
        [0.0] * (n * K),
    )
    # The kernel writes the LAPACK DPOTRF info into the first element of w.
    info = int(out[9][0])
    if info != 0:
        message = "sigma is not positive definite" if info > 0 else "input error for LAPACK DPOTRF"
        return _fail("VVV", n, p, G, K, parameters, warn, message, -9)
    return _from_kernel("VVV", n, p, G, K, out[11], float(out[10]), parameters, warn, "cannot compute E-step")
