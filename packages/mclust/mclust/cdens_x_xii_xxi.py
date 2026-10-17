"""Component densities for the X, XII, and XXI models of mclust 6.1.3 (mclust.R).

R's ``cdensX``, ``cdensXII``, and ``cdensXXI`` only call ``cdensE``, ``cdensEII``,
and ``cdensEEI`` and then set the model name. The same Fortran kernels are called
here directly, so the values match R: ``es1e`` for X, ``eseii`` for XII, and
``eseei`` for XXI, from the ``mclust_kernels`` module (crates/mclust). The mixing
proportions are not passed (``pro = -1``) and the result is an n x G array.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from mclust.cdens_vee_eve_vve import _any_missing
from mclust.mclust_options import mclust_options
from mclust_kernels import eseei, eseii, es1e

__all__ = ["cdens_x", "cdens_xii", "cdens_xxi"]

_EPS = float(np.finfo(float).eps)
# R: signif(.Machine$double.xmax, 6)
_LOGLIK_LIMIT = float("%.6g" % float(np.finfo(float).max))


def _finish(z: np.ndarray, loglik: float, logarithm: bool, warn: bool) -> np.ndarray:
    if loglik > _LOGLIK_LIMIT:
        warning = "sigma-squared falls below threshold"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
    elif not logarithm:
        z = np.exp(z)
    return z


def _missing_or_warn(n: int, G: int, parameters: dict[str, Any], warn: bool) -> np.ndarray | None:
    if any(parameters.get(k) is None for k in ("mean", "variance")) or _any_missing(
        [parameters.get(k) for k in ("mean", "variance")]
    ):
        if warn:
            warnings.warn("parameters are missing")
        return np.full((n, G), np.nan)
    return None


def cdens_x(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> np.ndarray:
    """Component densities for the X model (one-dimensional data, R ``cdensE``).

    Variance: ``sigmasq`` (scalar). Mean: length G. Returns an n x G array.
    """
    if warn is None:
        warn = bool(mclust_options("warn"))
    x = np.asarray(data, dtype=float)
    if x.ndim == 2 and x.shape[1] != 1:
        raise ValueError("data must be one-dimensional")
    x = x.reshape(-1)
    n = x.size
    mu = np.asarray(parameters["mean"], dtype=float).reshape(-1)
    G = mu.size

    missing = _missing_or_warn(n, G, parameters, warn)
    if missing is not None:
        return missing

    sigmasq = parameters["variance"].get("sigmasq")
    if sigmasq is None:
        raise ValueError("variance parameters are missing")
    sigmasq = np.asarray(sigmasq, dtype=float).reshape(-1)
    if sigmasq[0] < 0:
        raise ValueError("sigma-squared is negative")
    if not sigmasq[0]:
        if warn:
            warnings.warn("sigma-squared vanishes")
        return np.full((n, G), np.nan)

    out = es1e(
        (
            x.tolist(),
            mu.tolist(),
            float(sigmasq[0]),
            [-1.0],
            n,
            G,
            -1.0,
            0.0,
            [0.0] * (n * G),
        )
    )
    z = np.asarray(out[8], dtype=float).reshape((n, G), order="F")
    return _finish(z, float(out[7]), logarithm, warn)


def cdens_xii(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> np.ndarray:
    """Component densities for the XII model (R ``cdensEII``).

    Variance: ``sigmasq`` (scalar). Mean: p x G. Returns an n x G array.
    """
    if warn is None:
        warn = bool(mclust_options("warn"))
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    n, p = x.shape
    mu = np.asarray(parameters["mean"], dtype=float)
    if mu.ndim == 1:
        mu = mu.reshape(-1, 1)
    G = mu.shape[1]

    missing = _missing_or_warn(n, G, parameters, warn)
    if missing is not None:
        return missing

    sigmasq = parameters["variance"].get("sigmasq")
    if sigmasq is None:
        raise ValueError("variance parameters are missing")
    sigmasq = np.asarray(sigmasq, dtype=float).reshape(-1)
    if sigmasq[0] < 0:
        raise ValueError("sigma-squared is negative")
    if not sigmasq[0]:
        if warn:
            warnings.warn("sigma-squared vanishes")
        return np.full((n, G), np.nan)

    out = eseii(
        (
            x.ravel(order="F").tolist(),
            mu.ravel(order="F").tolist(),
            float(sigmasq[0]),
            [-1.0],
            n,
            p,
            G,
            -1.0,
            0.0,
            [0.0] * (n * G),
        )
    )
    z = np.asarray(out[9], dtype=float).reshape((n, G), order="F")
    return _finish(z, float(out[8]), logarithm, warn)


def cdens_xxi(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> np.ndarray:
    """Component densities for the XXI model (R ``cdensEEI``).

    Variance: ``scale`` (scalar), ``shape`` (length p). Mean: p x G.
    Returns an n x G array.
    """
    if warn is None:
        warn = bool(mclust_options("warn"))
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    n, p = x.shape
    mu = np.asarray(parameters["mean"], dtype=float)
    if mu.ndim == 1:
        mu = mu.reshape(-1, 1)
    G = mu.shape[1]

    missing = _missing_or_warn(n, G, parameters, warn)
    if missing is not None:
        return missing

    variance = parameters["variance"]
    if variance.get("scale") is None or variance.get("shape") is None:
        raise ValueError("variance parameters are missing")
    scale = float(np.asarray(variance["scale"], dtype=float).reshape(-1)[0])
    shape = np.asarray(variance["shape"], dtype=float).reshape(-1)

    out = eseei(
        (
            x.ravel(order="F").tolist(),
            mu.ravel(order="F").tolist(),
            scale,
            shape.tolist(),
            [-1.0],
            n,
            p,
            G,
            -1.0,
            0.0,
            [0.0] * (n * G),
        )
    )
    z = np.asarray(out[10], dtype=float).reshape((n, G), order="F")
    return _finish(z, float(out[9]), logarithm, warn)
