"""Relative curvature measures for nonlinear regression (``rms.curv``)."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from mass.errors import MassError


class _HasNlsModel(Protocol):
    m: Any


def _dnrm2(values: np.ndarray) -> float:
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


def _ddot(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(left, right))


def _linpack_qr(a: np.ndarray, tol: float = 1e-7) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """R ``qr(..., LAPACK = FALSE)`` storage, from LINPACK ``dqrdc2``."""
    matrix = np.array(a, dtype=np.float64, copy=True)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    n, p = matrix.shape
    x = matrix.copy()
    qraux = np.zeros(p)
    work = np.zeros(p)
    pivot = np.arange(1, p + 1)
    for j in range(p):
        qraux[j] = _dnrm2(x[:, j])
        work[j] = qraux[j]
    lup = min(n, p)
    k = p
    col = 0
    while col < lup:
        if col >= k:
            break
        if not (qraux[col] > tol * work[col]):
            if col != k - 1:
                x[:, [col, k - 1]] = x[:, [k - 1, col]]
                qraux[col], qraux[k - 1] = qraux[k - 1], qraux[col]
                work[col], work[k - 1] = work[k - 1], work[col]
                pivot[col], pivot[k - 1] = pivot[k - 1], pivot[col]
            k -= 1
            continue
        nrmxl = _dnrm2(x[col:, col])
        if nrmxl != 0.0:
            if x[col, col] != 0.0:
                nrmxl = math.copysign(nrmxl, float(x[col, col]))
            x[col:, col] = x[col:, col] / nrmxl
            x[col, col] = 1.0 + x[col, col]
            for j in range(col + 1, p):
                dot = _ddot(x[col:, col], x[col:, j])
                t = -dot / float(x[col, col])
                x[col:, j] = x[col:, j] + t * x[col:, col]
                if j < k and qraux[j] != 0.0:
                    tt = 1.0 - (abs(float(x[col, j])) / qraux[j]) ** 2
                    tt = max(tt, 0.0)
                    check = 1.0 + 0.05 * tt * (qraux[j] / work[j]) ** 2
                    if check == 1.0:
                        qraux[j] = _dnrm2(x[col + 1 :, j]) if col + 1 < n else 0.0
                    else:
                        qraux[j] = qraux[j] * math.sqrt(tt)
            qraux[col] = x[col, col]
            x[col, col] = -nrmxl
        else:
            qraux[col] = 0.0
        col += 1
    rank = k if col >= k else col
    return x, qraux, pivot, int(rank)


def _linpack_q(x: np.ndarray, qraux: np.ndarray, rank: int) -> np.ndarray:
    n = x.shape[0]
    result = np.eye(n)
    for col in range(int(rank) - 1, -1, -1):
        if qraux[col] == 0.0:
            continue
        reflector = x[col:, col].copy()
        reflector[0] = qraux[col]
        dots = reflector @ result[col:, :]
        scale = -dots / reflector[0]
        result[col:, :] = result[col:, :] + np.outer(reflector, scale)
    return result


def _qr_r(qr_matrix: np.ndarray) -> np.ndarray:
    """Upper triangle from R ``qr.R`` on LINPACK storage."""
    n, p = qr_matrix.shape
    rows = min(n, p)
    r_mat = np.array(qr_matrix[:rows, :], copy=True)
    for i in range(rows):
        for j in range(p):
            if i > j:
                r_mat[i, j] = 0.0
    return r_mat


def _qf(probability: float, df1: float, df2: float) -> float:
    from scipy.stats import f as f_dist

    return float(f_dist.ppf(probability, df1, df2))


def _as_matrix(value: Any, name: str) -> np.ndarray:
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 2:
        raise MassError(f'"{name}" must be a matrix')
    return arr


def _as_hessian(value: Any) -> np.ndarray:
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 3:
        raise MassError('"hessian" must be a 3-D array')
    return arr


@dataclass
class RmsCurv:
    """Result of ``rms.curv`` (class ``rms.curv`` in R)."""

    pe: float
    ic: float
    ct: float
    ci: float
    C: np.ndarray


def rms_curv(obj: _HasNlsModel) -> RmsCurv:
    """Root mean square parameter effects and intrinsic relative curvatures."""
    model = obj.m
    fit_val = model.fitted()
    v = getattr(fit_val, "gradient", None)
    if v is None:
        stop_msg = '"gradient" attribute missing'
        raise MassError(stop_msg)
    a = getattr(fit_val, "hessian", None)
    if a is None:
        stop_msg = '"hessian" attribute missing'
        raise MassError(stop_msg)
    v = _as_matrix(v, "gradient")
    a = _as_hessian(a)
    p = v.shape[1]
    n = v.shape[0]
    dev_attr = getattr(obj, "deviance", None)
    if callable(dev_attr):
        dev = float(dev_attr())
    elif dev_attr is not None:
        dev = float(dev_attr)
    else:
        raise MassError("object has no deviance")
    s = math.sqrt(dev / (n - p))
    sp = s * math.sqrt(p)
    design = v.copy()
    for j in range(p):
        design = np.column_stack([design, a[:, : j + 1, j]])
    qr_mat, qraux, _pivot, rank = _linpack_qr(design)
    q_mat = _linpack_q(qr_mat, qraux, rank)
    q1 = q_mat[:, :rank]
    if rank <= p:
        warnings.warn("regression apparently linear", stacklevel=2)
    c_arr = np.zeros((rank, p, p), dtype=float)
    for j in range(p):
        c_arr[:, :, j] = q1.T @ a[:, :, j]
    c_arr = np.transpose(c_arr, (1, 2, 0))
    r11 = _qr_r(qr_mat)[:p, :p]
    r11i = np.linalg.inv(r11)
    ct = 0.0
    for j in range(p):
        c_arr[:, :, j] = r11i.T @ c_arr[:, :, j] @ r11i * sp
        block = c_arr[:, :, j]
        ct += 2.0 * float(np.sum(block**2)) + float(np.sum(np.diag(block))) ** 2
    ci = 0.0
    for j in range(p, rank):
        c_arr[:, :, j] = r11i.T @ c_arr[:, :, j] @ r11i * sp
        block = c_arr[:, :, j]
        ci += 2.0 * float(np.sum(block**2)) + float(np.sum(np.diag(block))) ** 2
    ct = math.sqrt(ct / (p * (p + 2)))
    ci = math.sqrt(ci / (p * (p + 2)))
    f_scale = math.sqrt(_qf(19.0 / 20.0, p, n - p))
    pe = ct * f_scale
    ic = ci * f_scale
    return RmsCurv(pe=pe, ic=ic, ct=ct, ci=ci, C=c_arr)
