"""Drop redundant columns from rank-deficient design matrices (ordinal drop.coef)."""

from __future__ import annotations

import math

import numpy as np


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
    for a, b in zip(left, right):
        total += float(a) * float(b)
    return total


def _linpack_qr(x, tol=1e-7):
    """Rank and pivot from R's dqrdc2 (qr(..., LAPACK = FALSE))."""
    matrix = np.array(x, dtype=np.float64, copy=True)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    n, p = matrix.shape
    if n == 0 or p == 0:
        return np.arange(1, p + 1), 0
    qraux = [0.0] * p
    work1 = [0.0] * p
    work2 = [0.0] * p
    pivot = list(range(1, p + 1))
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
            piv = pivot[col:p]
            pivot[col : p - 1] = piv[1:]
            pivot[p - 1] = piv[0]
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
                diag = float(matrix[col, col])
                if diag != 0.0:
                    nrmxl = math.copysign(nrmxl, diag)
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
    rank = int(min(k - 1, n))
    return np.array(pivot, dtype=int), rank


def drop_coef(X, silent=False):
    """Return a full column-rank submatrix of a design matrix."""
    matrix = np.asarray(X, dtype=float)
    if matrix.ndim != 2:
        raise TypeError("X must be a matrix")
    silent = bool(silent)
    pivot, rank = _linpack_qr(matrix, tol=1e-7)
    ncol = matrix.shape[1]
    if rank == ncol:
        return matrix.copy()
    if not silent:
        dropped = ncol - rank
        print(f"design is column rank deficient so dropping {dropped} coef")
    sel = pivot[:rank] - 1
    new_x = matrix[:, sel].copy()
    verify_rank = int(np.linalg.matrix_rank(new_x))
    if rank != verify_rank:
        raise RuntimeError("determination of full column rank design matrix failed")
    return new_x
