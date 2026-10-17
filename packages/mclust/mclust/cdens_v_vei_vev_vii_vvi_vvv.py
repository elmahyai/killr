"""cdensV, cdensVEI, cdensVEV, cdensVII, cdensVVI, and cdensVVV of mclust 6.1.3 (mclust.R).

Each function follows the R wrapper: it checks the arguments, then calls one
Fortran kernel from ``mclust_kernels`` (``es1v``, ``esvii``, ``esvei``, ``esvev``,
``esvvi``, ``esvvv``). ``pro`` and ``Vinv`` are passed as -1, as the R wrappers do.
Arrays go to the kernels in column-major order. The kernels return every argument,
so the outputs are read by position.

Each function returns an n x G ``Cdens`` matrix (a numpy array) carrying the R
attributes ``logarithm``, ``modelName``, ``WARNING`` and ``returnCode``.
"""

from __future__ import annotations

import warnings
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
from mclust_kernels import es1v, esvei, esvev, esvii, esvvi, esvvv

__all__ = ["cdensV", "cdensVEI", "cdensVEV", "cdensVII", "cdensVVI", "cdensVVV", "Cdens"]

_MINUS_ONE = [-1.0]


def _parameters(parameters: dict[str, Any] | None) -> dict[str, Any]:
    if parameters is None:
        raise TypeError('argument "parameters" is missing, with no default')
    return parameters


def _variance(parameters: dict[str, Any]) -> dict[str, Any]:
    return parameters.get("variance") or {}


def _matrix(data: Any) -> np.ndarray:
    x = np.asarray(data, dtype=float)
    if x.ndim != 2:
        raise ValueError("data must be a matrix")
    return x


def _sigma_checks(sigmasq: Any) -> np.ndarray | None:
    """R: stop on a negative sigma-squared. Returns the array, or None when one vanishes."""
    if sigmasq is None:
        raise ValueError("variance parameters are missing")
    sig = np.asarray(sigmasq, dtype=float).reshape(-1)
    if np.any(sig < 0):
        raise ValueError("sigma-squared is negative")
    if np.any(sig == 0):
        return None
    return sig


def cdensV(
    data: Any,
    logarithm: bool = False,
    parameters: dict[str, Any] | None = None,
    warn: bool | None = None,
    **_: Any,
) -> Cdens:
    """Log (or, with logarithm=False, plain) component densities for the one-dimensional V model."""
    warn = warn_default(warn)
    parameters = _parameters(parameters)
    x = np.asarray(data, dtype=float)
    if x.ndim > 2 or (x.ndim == 2 and x.shape[1] != 1):
        raise ValueError("data must be one-dimensional")
    x = x.reshape(-1)
    n = x.size
    mu = np.asarray(parameters["mean"], dtype=float).reshape(-1)
    G = mu.size
    if has_na(parameters, ("pro", "mean", "variance")):
        return na_result("V", n, G, logarithm, warn, "parameters are missing", 9)
    sig = _sigma_checks(_variance(parameters).get("sigmasq"))
    if sig is None:
        return na_result("V", n, G, logarithm, warn, "sigma-squared vanishes", 9)
    if sig.size == 1:
        sig = np.repeat(sig, G)
    out = es1v(
        (col_major(x), col_major(mu), col_major(sig), _MINUS_ONE, n, G, -1.0, 0.0, [0.0] * (n * G))
    )
    return from_kernel("V", n, G, logarithm, out[8], float(out[7]), warn, "sigma-squared falls below threshold")


def cdensVII(
    data: Any,
    logarithm: bool = False,
    parameters: dict[str, Any] | None = None,
    warn: bool | None = None,
    **_: Any,
) -> Cdens:
    """Log (or plain) component densities for the VII model (spherical, variable volume)."""
    warn = warn_default(warn)
    parameters = _parameters(parameters)
    x = _matrix(data)
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]
    if has_na(parameters, ("pro", "mean", "variance")):
        return na_result("VII", n, G, logarithm, warn, "parameters are missing", 9)
    sig = _sigma_checks(_variance(parameters).get("sigmasq"))
    if sig is None:
        return na_result("VII", n, G, logarithm, warn, "sigma-squared vanishes", 9)
    out = esvii(
        (
            col_major(x),
            col_major(mu),
            col_major(sig),
            _MINUS_ONE,
            n,
            p,
            G,
            -1.0,
            0.0,
            [0.0] * (n * G),
        )
    )
    return from_kernel("VII", n, G, logarithm, out[9], float(out[8]), warn, "sigma-squared falls below threshold")


def cdensVEI(
    data: Any,
    logarithm: bool = False,
    parameters: dict[str, Any] | None = None,
    warn: bool | None = None,
    **_: Any,
) -> Cdens:
    """Log (or plain) component densities for the VEI model (diagonal, equal shape)."""
    warn = warn_default(warn)
    parameters = _parameters(parameters)
    x = _matrix(data)
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]
    if has_na(parameters, ("pro", "mean", "variance")):
        return na_result("VEI", n, G, logarithm, warn, "parameters are missing", 9)
    variance = _variance(parameters)
    require(variance, "scale", "shape")
    out = esvei(
        (
            col_major(x),
            col_major(mu),
            col_major(variance["scale"]),
            col_major(variance["shape"]),
            _MINUS_ONE,
            n,
            p,
            G,
            -1.0,
            0.0,
            [0.0] * (n * G),
        )
    )
    return from_kernel("VEI", n, G, logarithm, out[10], float(out[9]), warn, "cannot compute E-step")


def cdensVEV(
    data: Any,
    logarithm: bool = False,
    parameters: dict[str, Any] | None = None,
    warn: bool | None = None,
    **_: Any,
) -> Cdens:
    """Log (or plain) component densities for the VEV model (equal shape, variable orientation)."""
    warn = warn_default(warn)
    parameters = _parameters(parameters)
    x = _matrix(data)
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]
    if has_na(parameters, ("pro", "mean", "variance")):
        return na_result("VEV", n, G, logarithm, warn, "parameters are missing", 9)
    variance = _variance(parameters)
    require(variance, "scale", "shape", "orientation")
    out = esvev(
        (
            col_major(x),
            col_major(mu),
            col_major(variance["scale"]),
            col_major(variance["shape"]),
            orientation_arg(variance["orientation"], p, G),
            _MINUS_ONE,
            n,
            p,
            G,
            -1.0,
            [0.0] * p,
            [0.0] * p,
            0.0,
            [0.0] * (n * G),
        )
    )
    return from_kernel("VEV", n, G, logarithm, out[13], float(out[12]), warn, "cannot compute E-step")


def cdensVVI(
    data: Any,
    logarithm: bool = False,
    parameters: dict[str, Any] | None = None,
    warn: bool | None = None,
    **_: Any,
) -> Cdens:
    """Log (or plain) component densities for the VVI model (diagonal, variable volume and shape)."""
    warn = warn_default(warn)
    parameters = _parameters(parameters)
    x = _matrix(data)
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]
    # R checks the name "mu" here, which matches no element, so "mean" is not checked.
    if has_na(parameters, ("pro", "mu", "variance")):
        return na_result("VVI", n, G, logarithm, warn, "parameters are missing", 9)
    variance = _variance(parameters)
    require(variance, "scale", "shape")
    out = esvvi(
        (
            col_major(x),
            col_major(mu),
            col_major(variance["scale"]),
            col_major(variance["shape"]),
            _MINUS_ONE,
            n,
            p,
            G,
            -1.0,
            0.0,
            [0.0] * (n * G),
        )
    )
    return from_kernel("VVI", n, G, logarithm, out[10], float(out[9]), warn, "cannot compute E-step")


def cdensVVV(
    data: Any,
    logarithm: bool = False,
    parameters: dict[str, Any] | None = None,
    warn: bool | None = None,
    **_: Any,
) -> Cdens:
    """Log (or plain) component densities for the VVV model (ellipsoidal, variable everything).

    R returns a list in the missing-parameter branch. This returns the NA matrix with
    WARNING and returnCode 9, as the other cdens functions do.
    """
    warn = warn_default(warn)
    parameters = _parameters(parameters)
    x = _matrix(data)
    n, p = x.shape
    mu = as_mean_matrix(parameters["mean"])
    G = mu.shape[1]
    if has_na(parameters, ("pro", "mean", "variance")):
        return na_result("VVV", n, G, logarithm, warn, "parameters are missing", 9)
    variance = _variance(parameters)
    require(variance, "cholsigma")
    chol = np.asarray(variance["cholsigma"], dtype=float).reshape((p, p, G), order="F")
    out = esvvv(
        (
            1,
            col_major(x),
            col_major(mu),
            col_major(chol),
            _MINUS_ONE,
            n,
            p,
            G,
            -1.0,
            [0.0] * p,
            0.0,
            [0.0] * (n * G),
        )
    )
    # The kernel writes the LAPACK DPOTRF info into the first element of w.
    info = int(out[9][0])
    if info != 0:
        message = "sigma is not positive definite" if info > 0 else "input error for LAPACK DPOTRF"
        if warn:
            warnings.warn(message)
        return na_result("VVV", n, G, logarithm, False, message, -9)
    return from_kernel("VVV", n, G, logarithm, out[11], float(out[10]), warn, "cannot compute E-step")
