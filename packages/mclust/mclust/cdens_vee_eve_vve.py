"""Component densities for the VEE, EVE, and VVE models of mclust 6.1.3 (mclust.R / mclust2.R).

Each function is the R ``cdensVEE``, ``cdensEVE``, or ``cdensVVE``. The density is
computed by the Fortran kernels ``esvee``, ``eseve``, and ``esvve`` in the
``mclust_kernels`` module (crates/mclust). As in R, the mixing proportions are
not passed to the kernel (``pro = -1``), so the result is the component density
alone, one column per component.

The R function returns a matrix with ``logarithm``, ``modelName``, ``WARNING``
and ``returnCode`` attributes. Here the matrix is returned and any warning is
raised with ``warnings.warn`` when ``warn`` is set.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from mclust.mclust_options import mclust_options
from mclust_kernels import esvee, eseve, esvve

__all__ = ["cdens_vee", "cdens_eve", "cdens_vve"]

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


def _any_missing(values: list[Any]) -> bool:
    """True when any numeric leaf is NaN (R: any(is.na(unlist(...))))."""
    return any(np.isnan(v) for v in _numeric_leaves(values))


def _cdens_matrix(
    model_name: str,
    kernel: Any,
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool,
    warn: bool | None,
    scale_is_scalar: bool,
) -> np.ndarray:
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

    if any(parameters.get(k) is None for k in ("pro", "mean", "variance")) or _any_missing(
        [parameters.get(k) for k in ("pro", "mean", "variance")]
    ):
        warning = "parameters are missing"
        if warn:
            warnings.warn(warning)
        return np.full((n, G), np.nan)

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
    scale_arg: Any = float(scale.ravel()[0]) if scale_is_scalar else scale.ravel(order="F").tolist()
    shape_arg = shape.ravel(order="F").tolist()

    # Fortran arguments in R's .Fortran order; pro = -1 and Vinv = -1 as in R.
    out = kernel(
        (
            x_flat,
            [0.0] * (n * G),
            n,
            p,
            G,
            G,
            mu_flat,
            o_flat,
            scale_arg,
            shape_arg,
            [-1.0],
            -1.0,
            0.0,
            _EPS,
        )
    )
    z = np.asarray(out[1], dtype=float).reshape((n, G), order="F")
    loglik = float(out[12])

    if loglik > _LOGLIK_LIMIT:
        warning = "cannot compute E-step"
        if warn:
            warnings.warn(warning)
        z[:] = np.nan
    elif not logarithm:
        z = np.exp(z)
    return z


def cdens_vee(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> np.ndarray:
    """Component densities (or log densities) for the VEE model.

    Variance: ``scale`` (length G), ``shape`` (length p), ``orientation`` (p x p).
    Mean: p x G. Returns an n x G array.
    """
    return _cdens_matrix(
        "VEE", esvee, data, parameters, logarithm, warn, scale_is_scalar=False
    )


def cdens_eve(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> np.ndarray:
    """Component densities (or log densities) for the EVE model.

    Variance: ``scale`` (scalar), ``shape`` (p x G), ``orientation`` (p x p).
    Mean: p x G. Returns an n x G array.
    """
    return _cdens_matrix(
        "EVE", eseve, data, parameters, logarithm, warn, scale_is_scalar=True
    )


def cdens_vve(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> np.ndarray:
    """Component densities (or log densities) for the VVE model.

    Variance: ``scale`` (length G), ``shape`` (p x G), ``orientation`` (p x p).
    Mean: p x G. Returns an n x G array.
    """
    return _cdens_matrix(
        "VVE", esvve, data, parameters, logarithm, warn, scale_is_scalar=False
    )
