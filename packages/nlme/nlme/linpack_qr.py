"""R's LINPACK QR (``dqrdc2``, ``dqrsl``) and the BLAS calls they make.

``qr()``, ``qr.coef()``, ``qr.qty()``, ``qr.qy()``, ``qr.resid()`` and ``lm.fit``
reach R's ``appl/dqrdc2.f`` and ``appl/dqrsl.f``. Those routines call BLAS
``DNRM2``, ``DDOT``, ``DAXPY`` and ``DSCAL``; R on this machine links
``libblas.so.3``, which is OpenBLAS. The calls here go to the same library, so
the rounding of each step is R's. Summation order matters: ``nls`` iterates
with a numerical derivative whose step is about 1e-8 of the parameter, so a
one-ulp difference in an iterate moves the fitted values by about 1e-7.

Arrays are Fortran-ordered ``(n, p)`` float64 matrices, columns contiguous.
Indices in the comments are 1-based, as in the Fortran source.
"""

from __future__ import annotations

import ctypes
import math
from dataclasses import dataclass

import numpy as np

_blas = ctypes.CDLL("libblas.so.3")
_I = ctypes.c_int
_D = ctypes.c_double
_P = ctypes.c_void_p
_PI = ctypes.POINTER(_I)
_PD = ctypes.POINTER(_D)
_blas.ddot_.restype = _D
_blas.ddot_.argtypes = [_PI, _P, _PI, _P, _PI]
_blas.dnrm2_.restype = _D
_blas.dnrm2_.argtypes = [_PI, _P, _PI]
_blas.daxpy_.restype = None
_blas.daxpy_.argtypes = [_PI, _PD, _P, _PI, _P, _PI]
_blas.dscal_.restype = None
_blas.dscal_.argtypes = [_PI, _PD, _P, _PI]
_blas.dgemv_.restype = None
_blas.dgemv_.argtypes = [ctypes.c_char_p, _PI, _PI, _PD, _P, _PI, _P, _PI, _PD, _P, _PI]
_INC = _I(1)  # unit stride, shared; BLAS only reads it
_ONE = _D(1.0)
_ZERO = _D(0.0)

__all__ = [
    "QR",
    "dgemv",
    "dqrdc2",
    "dqrsl",
    "qr",
    "qr_coef",
    "qr_qty",
    "qr_qy",
    "qr_resid",
    "lm_fit_coef",
    "ld_sum",
    "r_mean",
]


def _addr(array: np.ndarray) -> int:
    return array.__array_interface__["data"][0]


def _dnrm2(vector: np.ndarray) -> float:
    if vector.shape[0] == 0:
        return 0.0
    n = _I(vector.shape[0])
    return float(_blas.dnrm2_(ctypes.byref(n), _addr(vector), ctypes.byref(_INC)))


def _ddot(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape[0] == 0:
        return 0.0
    n = _I(a.shape[0])
    return float(_blas.ddot_(ctypes.byref(n), _addr(a), ctypes.byref(_INC), _addr(b), ctypes.byref(_INC)))


def _daxpy(alpha: float, x: np.ndarray, y: np.ndarray) -> None:
    """``y += alpha * x`` in place, through BLAS ``DAXPY``."""
    if x.shape[0] == 0:
        return
    n = _I(x.shape[0])
    a = _D(alpha)
    _blas.daxpy_(ctypes.byref(n), ctypes.byref(a), _addr(x), ctypes.byref(_INC), _addr(y), ctypes.byref(_INC))


def _dscal(alpha: float, x: np.ndarray) -> None:
    if x.shape[0] == 0:
        return
    n = _I(x.shape[0])
    a = _D(alpha)
    _blas.dscal_(ctypes.byref(n), ctypes.byref(a), _addr(x), ctypes.byref(_INC))


def dgemv(a: np.ndarray, x: np.ndarray) -> np.ndarray:
    """``a %*% x`` the way R's ``matprod`` calls it: BLAS ``DGEMV`` with ``trans = "N"``.

    ``a`` is an ``(m, n)`` matrix and ``x`` a vector of length ``n``. R takes a
    vector-by-vector product ``x %*% y`` through the same call with ``m = 1``.
    """
    a = np.asfortranarray(a, dtype=np.float64)
    x = np.ascontiguousarray(x, dtype=np.float64)
    m, n = a.shape
    y = np.zeros(m, dtype=np.float64)
    if m == 0 or n == 0:
        return y
    mm = _I(m)
    nn = _I(n)
    lda = _I(m)
    _blas.dgemv_(
        b"N",
        ctypes.byref(mm),
        ctypes.byref(nn),
        ctypes.byref(_ONE),
        _addr(a),
        ctypes.byref(lda),
        _addr(x),
        ctypes.byref(_INC),
        ctypes.byref(_ZERO),
        _addr(y),
        ctypes.byref(_INC),
    )
    return y


def dqrdc2(x: np.ndarray, tol: float) -> tuple[int, np.ndarray, np.ndarray]:
    """Householder QR with R's limited column pivoting, in place on ``x``.

    Returns ``(rank, qraux, pivot)``. ``pivot`` is 1-based, as ``qr()$pivot``.
    """
    n, p = x.shape
    qraux = np.zeros(p, dtype=np.float64)
    work1 = np.zeros(p, dtype=np.float64)
    work2 = np.zeros(p, dtype=np.float64)
    pivot = np.arange(1, p + 1, dtype=np.int64)
    for j in range(p):
        qraux[j] = _dnrm2(x[:, j])
        work1[j] = qraux[j]
        work2[j] = qraux[j]
        if work2[j] == 0.0:
            work2[j] = 1.0
    lup = min(n, p)
    k = p + 1
    for l in range(1, lup + 1):
        # Move a negligible column to the end (cycle l..p left to right).
        while not (l >= k or qraux[l - 1] >= work2[l - 1] * tol):
            for i in range(n):
                t = x[i, l - 1]
                for j in range(l + 1, p + 1):
                    x[i, j - 2] = x[i, j - 1]
                x[i, p - 1] = t
            ipiv = pivot[l - 1]
            t = qraux[l - 1]
            tt = work1[l - 1]
            ttt = work2[l - 1]
            for j in range(l + 1, p + 1):
                pivot[j - 2] = pivot[j - 1]
                qraux[j - 2] = qraux[j - 1]
                work1[j - 2] = work1[j - 1]
                work2[j - 2] = work2[j - 1]
            pivot[p - 1] = ipiv
            qraux[p - 1] = t
            work1[p - 1] = tt
            work2[p - 1] = ttt
            k -= 1
        if l == n:
            continue
        col = x[l - 1 :, l - 1]
        nrmxl = _dnrm2(col)
        if nrmxl == 0.0:
            continue
        if x[l - 1, l - 1] != 0.0:
            nrmxl = math.copysign(nrmxl, x[l - 1, l - 1])
        _dscal(1.0 / nrmxl, col)
        x[l - 1, l - 1] = 1.0 + x[l - 1, l - 1]
        for j in range(l + 1, p + 1):
            cj = x[l - 1 :, j - 1]
            t = -_ddot(col, cj) / x[l - 1, l - 1]
            _daxpy(t, col, cj)
            if qraux[j - 1] != 0.0:
                ratio = abs(x[l - 1, j - 1]) / qraux[j - 1]
                tt = 1.0 - ratio * ratio
                tt = max(tt, 0.0)
                if abs(tt) >= 1e-6:
                    qraux[j - 1] = qraux[j - 1] * math.sqrt(tt)
                else:
                    qraux[j - 1] = _dnrm2(x[l:, j - 1])
                    work1[j - 1] = qraux[j - 1]
        qraux[l - 1] = x[l - 1, l - 1]
        x[l - 1, l - 1] = -nrmxl
    k = min(k - 1, n)
    return k, qraux, pivot


def dqrsl(x: np.ndarray, k: int, qraux: np.ndarray, y: np.ndarray, job: int) -> dict:
    """LINPACK ``dqrsl``. ``job`` picks the outputs as in the Fortran source.

    Returns a dict with ``qy``, ``qty``, ``b``, ``rsd``, ``xb`` (``None`` when not
    asked for) and ``info``. ``x`` is restored before returning.
    """
    n = x.shape[0]
    cqy = job // 10000 != 0
    cqty = job % 10000 != 0
    cb = (job % 1000) // 100 != 0
    cr = (job % 100) // 10 != 0
    cxb = job % 10 != 0
    ju = min(k, n - 1)
    out: dict = {"qy": None, "qty": None, "b": None, "rsd": None, "xb": None, "info": 0}
    y = np.ascontiguousarray(y, dtype=np.float64)
    if ju == 0:
        if cqy:
            out["qy"] = y.copy()
            out["qy"][0] = y[0]
        if cqty:
            out["qty"] = y.copy()
            out["qty"][0] = y[0]
        if cxb:
            out["xb"] = y.copy()
            out["xb"][0] = y[0]
        if cb:
            b = np.zeros(max(k, 1), dtype=np.float64)
            if x[0, 0] != 0.0:
                b[0] = y[0] / x[0, 0]
            else:
                out["info"] = 1
            out["b"] = b
        if cr:
            rsd = y.copy()
            rsd[0] = 0.0
            out["rsd"] = rsd
        return out

    qy = y.copy() if cqy else None
    qty = y.copy() if cqty else None
    if cqy:
        for j in range(ju, 0, -1):
            if qraux[j - 1] == 0.0:
                continue
            temp = x[j - 1, j - 1]
            x[j - 1, j - 1] = qraux[j - 1]
            col = x[j - 1 :, j - 1]
            t = -_ddot(col, qy[j - 1 :]) / x[j - 1, j - 1]
            _daxpy(t, col, qy[j - 1 :])
            x[j - 1, j - 1] = temp
    if cqty:
        for j in range(1, ju + 1):
            if qraux[j - 1] == 0.0:
                continue
            temp = x[j - 1, j - 1]
            x[j - 1, j - 1] = qraux[j - 1]
            col = x[j - 1 :, j - 1]
            t = -_ddot(col, qty[j - 1 :]) / x[j - 1, j - 1]
            _daxpy(t, col, qty[j - 1 :])
            x[j - 1, j - 1] = temp

    b = None
    if cb:
        b = qty[:k].copy()
    xb = None
    if cxb:
        xb = np.zeros(n, dtype=np.float64)
        xb[:k] = qty[:k]
    rsd = None
    if cr:
        rsd = np.zeros(n, dtype=np.float64)
        if k < n:
            rsd[k:] = qty[k:]
    if cb:
        for j in range(k, 0, -1):
            if x[j - 1, j - 1] == 0.0:
                out["info"] = j
                break
            b[j - 1] = b[j - 1] / x[j - 1, j - 1]
            if j != 1:
                t = -b[j - 1]
                _daxpy(t, np.ascontiguousarray(x[: j - 1, j - 1]), b[: j - 1])
    if cr or cxb:
        for j in range(ju, 0, -1):
            if qraux[j - 1] == 0.0:
                continue
            temp = x[j - 1, j - 1]
            x[j - 1, j - 1] = qraux[j - 1]
            col = x[j - 1 :, j - 1]
            if cr:
                t = -_ddot(col, rsd[j - 1 :]) / x[j - 1, j - 1]
                _daxpy(t, col, rsd[j - 1 :])
            if cxb:
                t = -_ddot(col, xb[j - 1 :]) / x[j - 1, j - 1]
                _daxpy(t, col, xb[j - 1 :])
            x[j - 1, j - 1] = temp

    out.update({"qy": qy, "qty": qty, "b": b, "rsd": rsd, "xb": xb})
    return out


@dataclass
class QR:
    """``qr()`` object: the factored matrix, ``qraux``, ``pivot`` and ``rank``."""

    qr: np.ndarray
    qraux: np.ndarray
    pivot: np.ndarray
    rank: int


def qr(x: np.ndarray, tol: float = 1e-7) -> QR:
    """``qr(x, tol)`` with the LINPACK method. ``x`` is copied."""
    mat = np.array(x, dtype=np.float64, order="F", copy=True)
    if mat.ndim == 1:
        mat = mat.reshape(-1, 1, order="F")
    rank, qraux, pivot = dqrdc2(mat, tol)
    return QR(qr=mat, qraux=qraux, pivot=pivot, rank=int(rank))


def qr_qty(obj: QR, y: np.ndarray) -> np.ndarray:
    """``qr.qty(obj, y)``: ``t(Q) %*% y``."""
    return dqrsl(obj.qr, obj.rank, obj.qraux, y, 1000)["qty"]


def qr_qy(obj: QR, y: np.ndarray) -> np.ndarray:
    """``qr.qy(obj, y)``: ``Q %*% y``."""
    return dqrsl(obj.qr, obj.rank, obj.qraux, y, 10000)["qy"]


def qr_resid(obj: QR, y: np.ndarray) -> np.ndarray:
    """``qr.resid(obj, y)``."""
    return dqrsl(obj.qr, obj.rank, obj.qraux, y, 10)["rsd"]


def qr_coef(obj: QR, y: np.ndarray) -> np.ndarray:
    """``qr.coef(obj, y)`` for a full-rank object."""
    if obj.rank < obj.qr.shape[1]:
        raise NotImplementedError("qr.coef with a rank-deficient QR is not translated")
    out = dqrsl(obj.qr, obj.rank, obj.qraux, y, 100)
    if out["info"] != 0:
        raise ValueError("singular triangular factor")
    return out["b"]


def lm_fit_coef(x: np.ndarray, y: np.ndarray, tol: float = 1e-7) -> np.ndarray:
    """``lm.fit(x, y)$coefficients`` for a full-rank ``x``: ``dqrls`` (``dqrdc2`` + ``dqrsl`` 1110)."""
    mat = np.array(x, dtype=np.float64, order="F", copy=True)
    rank, qraux, _pivot = dqrdc2(mat, tol)
    if rank < mat.shape[1]:
        raise NotImplementedError("lm.fit with a rank-deficient model is not translated")
    out = dqrsl(mat, rank, qraux, np.asarray(y, dtype=np.float64), 1110)
    return out["b"]


def ld_sum(values) -> float:
    """``sum(values)`` in R: a long double accumulator, sequential."""
    arr = np.asarray(values, dtype=np.float64).astype(np.longdouble)
    if arr.size == 0:
        return 0.0
    return float(np.cumsum(arr)[-1])


def r_mean(values) -> float:
    """``mean(values)`` in R (``summary.c`` ``real_mean``): long double, with the second pass."""
    arr = np.asarray(values, dtype=np.float64).astype(np.longdouble)
    n = np.longdouble(arr.size)
    s = np.cumsum(arr)[-1] / n
    if math.isfinite(float(s)):
        t = np.cumsum(arr - s)[-1]
        s = s + t / n
    return float(s)
