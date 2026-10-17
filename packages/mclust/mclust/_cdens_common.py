"""Shared steps for the mclust cdens functions (cdensV, cdensVEI, ..., cdensEVV).

The cdens functions evaluate component log densities with the same Fortran
kernels the E-step uses, but with no mixing proportions and no noise component:
the R wrappers pass -1 for ``pro`` and ``Vinv``. The kernels come from the
``mclust_kernels`` binding built from ``crates/mclust``. Each binding function takes
one tuple of arguments and returns a list in the same order.
"""

from __future__ import annotations

import sys
import warnings
from typing import Any

import numpy as np

from mclust._estep_common import col_major, warn_default, z_from_kernel

__all__ = [
    "Cdens",
    "LOGLIK_LIMIT",
    "cdens_result",
    "col_major",
    "from_kernel",
    "has_na",
    "na_result",
    "orientation_arg",
    "require",
    "warn_default",
]

# R: signif(.Machine$double.xmax, 6)
LOGLIK_LIMIT = float("%.6g" % sys.float_info.max)


class Cdens(np.ndarray):
    """The n x G matrix that R's cdens functions return.

    The R attributes ``logarithm``, ``modelName``, ``WARNING`` and ``returnCode``
    are carried as Python attributes.
    """


def cdens_result(z: Any, model: str, logarithm: bool, warning: str | None, return_code: int) -> Cdens:
    out = np.asarray(z, dtype=float).view(Cdens)
    out.logarithm = bool(logarithm)
    out.modelName = model
    out.WARNING = warning
    out.returnCode = return_code
    return out


def na_result(
    model: str, n: int, G: int, logarithm: bool, warn: bool, message: str, return_code: int
) -> Cdens:
    """The R branches that return an NA matrix with a WARNING."""
    if warn:
        warnings.warn(message)
    return cdens_result(np.full((n, G), np.nan), model, logarithm, message, return_code)


def from_kernel(
    model: str,
    n: int,
    G: int,
    logarithm: bool,
    z_flat: Any,
    loglik: float,
    warn: bool,
    message: str,
) -> Cdens:
    """R: if (loglik > signif(.Machine$double.xmax, 6)) NA, else exp(z) unless logarithm."""
    if loglik > LOGLIK_LIMIT:
        return na_result(model, n, G, logarithm, warn, message, -1)
    z = z_from_kernel(z_flat, n, G)
    if not logarithm:
        z = np.exp(z)
    return cdens_result(z, model, logarithm, None, 0)


def _leaf_has_na(value: Any) -> bool:
    if value is None or isinstance(value, str):
        return False
    if isinstance(value, dict):
        return any(_leaf_has_na(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_leaf_has_na(v) for v in value)
    arr = np.asarray(value)
    return arr.dtype.kind == "f" and bool(np.isnan(arr).any())


def has_na(parameters: dict[str, Any], keys: tuple[str, ...]) -> bool:
    """R: any(is.na(unlist(parameters[keys]))). NULL entries drop out, as unlist does."""
    return any(_leaf_has_na(parameters.get(k)) for k in keys)


def require(variance: dict[str, Any], *keys: str) -> None:
    if any(variance.get(k) is None for k in keys):
        raise ValueError("variance parameters are missing")


def orientation_arg(orientation: Any, p: int, G: int) -> list[float]:
    """R: as.double(aperm(O, c(2, 1, 3)))."""
    o = np.asarray(orientation, dtype=float).reshape((p, p, G), order="F")
    return col_major(np.transpose(o, (1, 0, 2)))
