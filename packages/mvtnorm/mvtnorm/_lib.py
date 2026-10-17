"""The Genz–Bretz, TVPACK, and Miwa routines compiled in the mvtdst crate."""

from __future__ import annotations

import ctypes
import math
from pathlib import Path

import numpy as np
from scipy.stats import chi2, norm, t

from boot.rng import unif

_D = ctypes.c_double
_I = ctypes.c_int
_UNIF = ctypes.CFUNCTYPE(_D)
_PN = ctypes.CFUNCTYPE(_D, _D)
_PT = ctypes.CFUNCTYPE(_D, _I, _D)

_LIB = None
_KEEP = []


def _library():
    global _LIB
    if _LIB is not None:
        return _LIB
    path = Path(__file__).with_name("libmvtdst.so")
    lib = ctypes.CDLL(str(path))
    lib.mvn_miwa.restype = _D

    def pnorm(x):
        return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))

    def qnorm(p):
        return float(norm.ppf(float(p)))

    def pt(nu, x):
        if int(nu) <= 0:
            return pnorm(x)
        return float(t.cdf(float(x), int(nu)))

    def sqrt_qchisq(n, p):
        return math.sqrt(float(chi2.ppf(float(p), int(n))))

    cbs = (
        _UNIF(lambda: unif()),
        _PN(pnorm),
        _PN(qnorm),
        _PT(pt),
        _PT(sqrt_qchisq),
    )
    _KEEP.extend(cbs)
    lib.mvn_set_callbacks(*cbs)
    _LIB = lib
    return lib


def pack_corr(corr: np.ndarray) -> np.ndarray:
    """R's upper.tri after refilling the matrix by row."""
    n = corr.shape[0]
    filled = np.array(corr, dtype=float, order="F").ravel(order="F").reshape((n, n), order="C")
    mask = np.triu(np.ones((n, n), dtype=bool), 1)
    return np.ascontiguousarray(filled.ravel(order="F")[mask.ravel(order="F")])


def mvtdst_df(n, df, lower, upper, infin, correl, delta, maxpts, abseps, releps):
    lib = _library()
    lower = np.ascontiguousarray(lower, dtype=float)
    upper = np.ascontiguousarray(upper, dtype=float)
    infin = np.ascontiguousarray(infin, dtype=np.int32)
    correl = np.ascontiguousarray(correl, dtype=float)
    delta = np.ascontiguousarray(delta, dtype=float)
    err = _D(0.0)
    val = _D(0.0)
    info = _I(0)
    lib.mvn_mvtdst(
        _I(int(n)),
        _I(int(df)),
        lower.ctypes.data_as(ctypes.POINTER(_D)),
        upper.ctypes.data_as(ctypes.POINTER(_D)),
        infin.ctypes.data_as(ctypes.POINTER(_I)),
        correl.ctypes.data_as(ctypes.POINTER(_D)),
        delta.ctypes.data_as(ctypes.POINTER(_D)),
        _I(int(maxpts)),
        _D(float(abseps)),
        _D(float(releps)),
        ctypes.byref(err),
        ctypes.byref(val),
        ctypes.byref(info),
    )
    return val.value, err.value, int(info.value)


def tvtl(nu, h, r, epsi):
    lib = _library()
    h = np.ascontiguousarray(h, dtype=float)
    r = np.ascontiguousarray(r, dtype=float)
    out = _D(0.0)
    lib.mvn_tvtl(
        _I(int(nu)),
        h.ctypes.data_as(ctypes.POINTER(_D)),
        r.ctypes.data_as(ctypes.POINTER(_D)),
        _D(float(epsi)),
        ctypes.byref(out),
    )
    return out.value


def bvtl(nu, dh, dk, r):
    lib = _library()
    out = _D(0.0)
    lib.mvn_bvtl(_I(int(nu)), _D(float(dh)), _D(float(dk)), _D(float(r)), ctypes.byref(out))
    return out.value


def miwa(steps, corr, upper, lower, infin):
    lib = _library()
    dim = int(len(upper))
    corr = np.ascontiguousarray(np.array(corr, dtype=float, order="F"))
    upper = np.ascontiguousarray(upper, dtype=float)
    lower = np.ascontiguousarray(lower, dtype=float)
    infin = np.ascontiguousarray(infin, dtype=np.int32)
    return float(
        lib.mvn_miwa(
            _I(int(steps)),
            _I(dim),
            corr.ctypes.data_as(ctypes.POINTER(_D)),
            upper.ctypes.data_as(ctypes.POINTER(_D)),
            lower.ctypes.data_as(ctypes.POINTER(_D)),
            infin.ctypes.data_as(ctypes.POINTER(_I)),
        )
    )
