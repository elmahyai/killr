"""Rank of a square matrix, from matrixcalc 1.0-6."""

from __future__ import annotations

import math

import numpy as np

from matrixcalc.is_square_matrix import is_square_matrix


def matrix_rank(x, method="qr"):
    """Return the rank of a square numeric matrix.

    ``method`` is ``"qr"`` (default) or ``"chol"``. A non-square matrix raises
    ``argument x is not a square matrix``.
    """
    if not is_square_matrix(x):
        raise ValueError("argument x is not a square matrix")
    if isinstance(method, (list, tuple)):
        method = method[0] if method else "qr"
    elif isinstance(method, np.ndarray):
        flat = np.ravel(method)
        method = flat[0] if flat.size else "qr"
    method = str(method)
    array = _as_matrix(x)
    matrix = np.asarray(array, dtype=float)
    if method == "chol":
        return _chol_rank(matrix)
    return _qr_rank(matrix)


def _qr_rank(matrix):
    """R ``qr(x)$rank`` with the default LINPACK path."""
    return _linpack_qr_rank(matrix)


def _chol_rank(matrix):
    """R ``attr(chol(x, pivot = TRUE), "rank")``."""
    from scipy.linalg.lapack import dpstrf

    n = matrix.shape[0]
    if n == 0:
        return 0
    _factor, _piv, rank, info = dpstrf(np.array(matrix, dtype=np.float64, copy=True), lower=0)
    if info < 0:
        raise np.linalg.LinAlgError("dpstrf failed")
    return int(rank)


def _linpack_qr_rank(x, tol=1e-7):
    matrix = np.array(x, dtype=np.float64, copy=True)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    n, p = matrix.shape
    if n == 0 or p == 0:
        return 0
    qraux = [0.0] * p
    work1 = [0.0] * p
    work2 = [0.0] * p
    for j in range(p):
        qraux[j] = _dnrm2(matrix[:, j])
        work1[j] = qraux[j]
        work2[j] = qraux[j] if qraux[j] != 0.0 else 1.0
    lup = min(n, p)
    k = p + 1
    for col in range(lup):
        while (col + 1) < k and qraux[col] < work2[col] * tol:
            block = matrix[:, col:p].copy()
            matrix[:, col : p - 1] = block[:, 1:]
            matrix[:, p - 1] = block[:, 0]
            saved_q, saved_1, saved_2 = qraux[col], work1[col], work2[col]
            for j in range(col, p - 1):
                qraux[j] = qraux[j + 1]
                work1[j] = work1[j + 1]
                work2[j] = work2[j + 1]
            qraux[p - 1] = saved_q
            work1[p - 1] = saved_1
            work2[p - 1] = saved_2
            k -= 1
        if (col + 1) != n:
            nrmxl = _dnrm2(matrix[col:, col])
            if nrmxl != 0.0:
                pivot = float(matrix[col, col])
                if pivot != 0.0:
                    nrmxl = math.copysign(nrmxl, pivot)
                matrix[col:, col] = matrix[col:, col] / nrmxl
                matrix[col, col] = 1.0 + float(matrix[col, col])
                if p >= col + 2:
                    for j in range(col + 1, p):
                        dot = _ddot(matrix[col:, col], matrix[col:, j])
                        scale = -dot / float(matrix[col, col])
                        matrix[col:, j] = matrix[col:, j] + scale * matrix[col:, col]
                        if qraux[j] != 0.0:
                            entry = abs(float(matrix[col, j])) / qraux[j]
                            tt = 1.0 - entry * entry
                            if tt < 0.0:
                                tt = 0.0
                            if abs(tt) >= 1e-6:
                                qraux[j] = qraux[j] * math.sqrt(tt)
                            else:
                                qraux[j] = _dnrm2(matrix[col + 1 :, j])
                                work1[j] = qraux[j]
                qraux[col] = float(matrix[col, col])
                matrix[col, col] = -nrmxl
    return int(min(k - 1, n))


def _dnrm2(values):
    scale = 0.0
    ssq = 1.0
    for value in values:
        value = float(value)
        if value != 0.0:
            absxi = abs(value)
            if scale < absxi:
                ratio = scale / absxi
                ssq = 1.0 + ssq * ratio * ratio
                scale = absxi
            else:
                ratio = absxi / scale
                ssq = ssq + ratio * ratio
    return scale * math.sqrt(ssq)


def _ddot(left, right):
    total = 0.0
    for a, b in zip(left, right, strict=False):
        total += float(a) * float(b)
    return total


def _as_matrix(x):
    if isinstance(x, np.ndarray):
        if x.ndim != 2:
            raise ValueError("argument x is not a matrix")
        return x
    if _rectangular_rows(x):
        return np.array(x)
    raise ValueError("argument x is not a matrix")


def _rectangular_rows(x):
    if isinstance(x, (str, bytes)) or not isinstance(x, (list, tuple)):
        return False
    if len(x) == 0:
        return False
    width = None
    for row in x:
        if isinstance(row, (str, bytes)) or not isinstance(row, (list, tuple)):
            return False
        if width is None:
            width = len(row)
        elif len(row) != width:
            return False
    return True
