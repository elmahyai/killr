"""Row-wise softmax from log scores (``softmax``)."""

from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["softmax"]

_LIB: ctypes.CDLL | None = None


def _lib() -> ctypes.CDLL:
    global _LIB
    if _LIB is None:
        so = Path(__file__).resolve().parents[3] / "crates" / "mclustbootstraplrt" / "libmclust_fortran.so"
        if not so.is_file():
            raise FileNotFoundError(f"mclust Fortran library missing: {so}")
        _LIB = ctypes.CDLL(str(so))
    return _LIB


def _i32(x: int) -> ctypes.c_int:
    return ctypes.c_int(int(x))


def softmax(x: Any, v: Any | None = None) -> np.ndarray:
    """Softmax rows of ``x`` with optional per-column shift ``v`` (Fortran kernel)."""
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        mat = arr.reshape(1, -1)
    else:
        mat = np.asfortranarray(arr)
    n, k = mat.shape
    if v is None:
        shift = np.zeros(k, dtype=float)
    else:
        shift = np.asarray(v, dtype=float).ravel()
    if shift.size != k:
        raise ValueError("length(v) == ncol(x) is not TRUE")
    lse = np.zeros(n, dtype=float)
    zflat = np.zeros(n * k, dtype=float)
    _lib().softmax_(
        mat.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(_i32(n)),
        ctypes.byref(_i32(k)),
        shift.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        lse.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        zflat.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    return zflat.reshape(n, k, order="F")
