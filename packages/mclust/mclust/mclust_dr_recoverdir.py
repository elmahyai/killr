"""Recover linear coefficients for MclustDR directions (``MclustDRrecoverdir``)."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

__all__ = ["MclustDRrecoverdir"]


def _is_mclust_dr(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        return "dir" in obj and "numdir" in obj and "x" in obj
    return hasattr(obj, "dir") and hasattr(obj, "numdir")


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)


def _normalize(vec: np.ndarray) -> np.ndarray:
    v = np.asarray(vec, dtype=float).reshape(-1)
    return v / np.sqrt(float(v @ v))


def MclustDRrecoverdir(
    object: Any,
    data: np.ndarray | None = None,
    *,
    normalized: bool = True,
    std: bool = False,
) -> np.ndarray:
    """Coefficients of the linear combination defining MclustDR directions."""
    if not _is_mclust_dr(object):
        raise ValueError("first argument must be an object of class 'MclustDR'")
    if data is None:
        x = np.asarray(_field(object, "x"), dtype=float)
    else:
        x = np.asarray(data, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    x = x - x.mean(axis=0, keepdims=True)
    numdir = int(_field(object, "numdir"))
    direction = np.asarray(_field(object, "dir"), dtype=float)
    if direction.ndim == 1:
        direction = direction.reshape(-1, 1)
    direction = direction[:, :numdir]
    b = np.linalg.lstsq(x, direction, rcond=None)[0]
    if std:
        # R: sdx <- sd(x). On a matrix, sd() pools every entry (sd(as.double(x))),
        # so sdx is one scalar, not one value per column.
        sdx = float(np.std(x, ddof=1))
        b = b * sdx
    if normalized:
        b = np.column_stack([_normalize(b[:, j]) for j in range(b.shape[1])])
    return b
