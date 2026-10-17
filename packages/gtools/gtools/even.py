"""Detect even integers (gtools 3.9.5 ``even``)."""

from __future__ import annotations

import numpy as np

_NA_INT = np.int32(-(2**31))
_NA_LOGICAL = np.int8(2)


def _as_numeric(x) -> np.ndarray:
    if isinstance(x, np.ndarray):
        if x.dtype.kind == "b":
            return x.astype(np.float64, copy=False)
        if x.dtype.kind == "i":
            out = x.astype(np.float64, copy=True)
            out[x == _NA_INT] = np.nan
            return out
        if x.dtype.kind in "fd":
            return np.asarray(x, dtype=np.float64)
        if x.dtype.kind == "U":
            out = np.empty(x.size, dtype=np.float64)
            out[:] = np.nan
            return out.reshape(x.shape)
        raise TypeError("numeric vector expected")
    if isinstance(x, (bool, np.bool_)):
        return np.array([float(x)], dtype=np.float64)
    if isinstance(x, (int, np.integer)) and not isinstance(x, (bool, np.bool_)):
        if np.int32(x) == _NA_INT:
            return np.array([np.nan], dtype=np.float64)
        return np.array([float(x)], dtype=np.float64)
    if isinstance(x, (float, np.floating)):
        return np.array([float(x)], dtype=np.float64)
    if isinstance(x, str):
        return np.array([np.nan], dtype=np.float64)
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            return np.array([], dtype=np.float64)
        return np.concatenate([_as_numeric(item) for item in x])
    raise TypeError("numeric vector expected")


def even(x):
    """Return ``TRUE`` where ``x`` is an even integer (``x %% 2 == 0``)."""
    values = _as_numeric(x)
    if values.size == 0:
        return np.array([], dtype=np.int8)

    with np.errstate(invalid="ignore"):
        mod = np.mod(values, 2.0)
    out = np.zeros(values.shape, dtype=np.int8)
    missing = np.isnan(values) | np.isnan(mod)
    out[missing] = _NA_LOGICAL
    even_mask = (~missing) & (mod == 0)
    out[even_mask] = np.int8(1)
    return out
