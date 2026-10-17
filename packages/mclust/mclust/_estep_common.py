"""Shared steps for the mclust E-step functions (estepE, estepEEE, estepEEI, estepEEV, estepEII, estepEVI).

The Fortran kernels come from the ``mclust_kernels`` binding built from ``crates/mclust``.
Each binding function takes one tuple of arguments and returns a list in the same order,
with the mutated arrays in place. Logical flags are passed as 0/1 integers.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from mclust.mclust_options import mclust_options
from mclust.utility_functions import hypvol

# signif(.Machine$double.xmax, 6) in R
DBL_MAX_SIGNIF = 1.79769e308


def warn_default(warn: Any) -> bool:
    """R: if (is.null(warn)) warn <- mclust.options("warn")."""
    if warn is None:
        return bool(mclust_options("warn"))
    return bool(warn)


def col_major(a: Any) -> list[float]:
    """Flatten an array in Fortran (column-major) order, as R's as.double does."""
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def as_mean_matrix(mean: Any) -> np.ndarray:
    """R: as.matrix(parameters$mean) for a p x G mean."""
    mu = np.asarray(mean, dtype=float)
    if mu.ndim == 1:
        mu = mu.reshape(-1, 1)
    return mu


def mixing_setup(parameters: dict[str, Any], data: np.ndarray, G: int) -> tuple[np.ndarray, int, float]:
    """Normalise pro and work out K and Vinv, following the R estep functions.

    Returns (pro, K, vinv). vinv is -1 when there is no noise component.
    """
    pro = np.asarray(parameters["pro"], dtype=float).ravel()
    pro = pro / pro.sum()
    l = pro.size
    if l == G + 1:
        vinv = parameters.get("Vinv")
        if vinv is None or vinv <= 0:
            vinv = hypvol(data, reciprocal=True)
        return pro, G + 1, float(vinv)
    if l != G:
        raise ValueError("pro improperly specified")
    return pro, G, -1.0


def _any_na(value: Any) -> bool:
    if value is None or isinstance(value, str):
        return False
    if isinstance(value, dict):
        return any(_any_na(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_any_na(v) for v in value)
    return bool(np.isnan(np.asarray(value, dtype=float)).any())


def has_missing_parameters(parameters: dict[str, Any]) -> bool:
    """R: any(is.na(unlist(parameters[c("pro", "mean", "variance")]))) or any(is.null(...))."""
    for key in ("pro", "mean", "variance"):
        value = parameters.get(key)
        if value is None or _any_na(value):
            return True
    return False


def result(
    model: str,
    n: int,
    d: int,
    G: int,
    z: np.ndarray,
    parameters: dict[str, Any],
    loglik: float,
    warning: str | None,
    return_code: int,
) -> dict[str, Any]:
    """The list R returns, with WARNING and returnCode carried as keys."""
    return {
        "modelName": model,
        "n": n,
        "d": d,
        "G": G,
        "z": z,
        "parameters": parameters,
        "loglik": loglik,
        "WARNING": warning,
        "returnCode": return_code,
    }


def missing_result(
    model: str, n: int, d: int, G: int, K: int, parameters: dict[str, Any], warn: bool
) -> dict[str, Any]:
    warning = "parameters are missing"
    if warn:
        warnings.warn(warning)
    z = np.full((n, K), np.nan)
    return result(model, n, d, G, z, parameters, float("nan"), warning, 9)


def z_from_kernel(flat: Any, n: int, K: int) -> np.ndarray:
    """R: matrix(temp, n, K), which fills column by column."""
    return np.asarray(flat, dtype=float).reshape((n, K), order="F")
