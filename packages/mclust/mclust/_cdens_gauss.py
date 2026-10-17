"""Shared steps for the Gaussian cdens functions cdensE, cdensEII, cdensEEI, cdensEVI, cdensEEV and cdensEEE.

The Fortran kernels are called with the mixing proportions set to -1, as R does. The kernel then
returns the unnormalised component log densities, one column per component.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from mclust._estep_common import DBL_MAX_SIGNIF, col_major, warn_default, z_from_kernel

__all__ = [
    "DBL_MAX_SIGNIF",
    "col_major",
    "warn_default",
    "z_from_kernel",
    "has_missing",
    "cdens_result",
    "missing_cdens",
]


def _any_na(value: Any) -> bool:
    if value is None or isinstance(value, str):
        return False
    if isinstance(value, dict):
        return any(_any_na(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_any_na(v) for v in value)
    return bool(np.isnan(np.asarray(value, dtype=float)).any())


def has_missing(parameters: dict[str, Any], keys: tuple[str, ...]) -> bool:
    """R: any(is.na(unlist(parameters[keys]))) or any(is.null(parameters[keys]))."""
    for key in keys:
        value = parameters.get(key)
        if value is None or _any_na(value):
            return True
    return False


def cdens_result(
    model: str, z: np.ndarray, logarithm: bool, warning: str | None, return_code: int
) -> dict[str, Any]:
    """The matrix R returns, with the logarithm, modelName, WARNING and returnCode attributes."""
    return {
        "z": z,
        "logarithm": logarithm,
        "modelName": model,
        "WARNING": warning,
        "returnCode": return_code,
    }


def missing_cdens(model: str, n: int, G: int, logarithm: bool, warn: bool, warning: str) -> dict[str, Any]:
    """An all-NA result with return code 9, as R returns it on missing or vanishing parameters."""
    if warn:
        warnings.warn(warning)
    z = np.full((n, G), np.nan)
    return cdens_result(model, z, logarithm, warning, 9)
