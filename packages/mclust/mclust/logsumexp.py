"""Row-wise log-sum-exp with optional shift vector (``logsumexp``)."""

from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["logsumexp"]

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


def logsumexp(x: Any, v: Any | None = None) -> np.ndarray:
    """``log(sum(exp(x_ij + v_j)))`` for each row ``i`` (Fortran kernel)."""
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
    _lib().logsumexp_(
        mat.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(_i32(n)),
        ctypes.byref(_i32(k)),
        shift.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        lse.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    return lse
