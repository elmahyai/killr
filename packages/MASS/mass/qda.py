"""Quadratic discriminant analysis (MASS qda)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from mass.errors import MassError

_PRIOR_PROPORTIONS = object()


@dataclass
class QdaFit:
    prior: np.ndarray
    counts: np.ndarray
    means: np.ndarray
    scaling: np.ndarray
    ldet: np.ndarray
    lev: np.ndarray
    n: int
    call: Any = None
    terms: Any = None
    contrasts: Any = None
    xlevels: Any = None
    na_action: Any = None
    method: str = "moment"


@dataclass
class QdaCvResult:
    class_: np.ndarray
    posterior: np.ndarray


def _dnrm2(values) -> float:
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


def _ddot(left, right) -> float:
    total = 0.0
    for a, b in zip(left, right, strict=False):
        total += float(a) * float(b)
    return total


def _linpack_qr(x: np.ndarray, tol: float = 1e-7) -> tuple[np.ndarray, int]:
    """R default qr (LAPACK=FALSE) storage and rank."""
    matrix = np.array(x, dtype=np.float64, copy=True)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    n, p = matrix.shape
    if n == 0 or p == 0:
        return matrix, 0
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
    rank = int(min(k - 1, n))
    return matrix, rank


def _backsolve_upper(r: np.ndarray, b: np.ndarray) -> np.ndarray:
    """R backsolve on the upper triangle of the first p rows of qr."""
    p = r.shape[0]
    b = np.asarray(b, dtype=float)
    if b.ndim == 1:
        b = b.reshape(p, 1)
    x = np.zeros_like(b, dtype=float)
    for i in range(p - 1, -1, -1):
        row = r[i, i + 1 : p]
        x[i, :] = (b[i, :] - row @ x[i + 1 : p, :]) / r[i, i]
    return x if b.shape[1] > 1 else x[:, 0]


def _as_factor(grouping) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(grouping)
    if arr.dtype.kind in "OUS":
        lev, codes = np.unique(arr, return_inverse=True)
        return lev, codes.astype(int)
    lev, codes = np.unique(arr, return_inverse=True)
    return lev, codes.astype(int)


def _group_means(x: np.ndarray, codes: np.ndarray, ng: int) -> np.ndarray:
    p = x.shape[1]
    means = np.zeros((ng, p), dtype=float)
    for i in range(ng):
        means[i, :] = x[codes == i, :].mean(axis=0)
    return means


def _scale_center(x: np.ndarray, center: np.ndarray) -> np.ndarray:
    return x - center


def _cov_mve(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    raise MassError("cov.mve is not translated in this package yet")


def _qda_default(
    x: np.ndarray,
    grouping,
    *,
    prior=_PRIOR_PROPORTIONS,
    method: str = "moment",
    cv: bool = False,
    nu: float = 5.0,
) -> QdaFit | QdaCvResult:
    if x.ndim != 2:
        raise MassError("'x' is not a matrix")
    x = np.asarray(x, dtype=float)
    if not np.all(np.isfinite(x)):
        raise MassError("infinite, NA or NaN values in 'x'")
    n, p = x.shape
    lev, codes = _as_factor(grouping)
    if n != len(codes):
        raise MassError("nrow(x) and length(grouping) are different")
    counts = np.bincount(codes, minlength=len(lev)).astype(float)
    if np.any(counts < p + 1):
        raise MassError("some group is too small for 'qda'")
    proportions = counts / len(codes)
    ng = len(proportions)
    if prior is _PRIOR_PROPORTIONS:
        prior_arr = proportions.copy()
    else:
        prior_arr = np.asarray(prior, dtype=float).reshape(-1)
    if np.any(prior_arr < 0) or round(float(np.sum(prior_arr)), 5) != 1.0:
        raise MassError("invalid 'prior'")
    if len(prior_arr) != ng:
        raise MassError("'prior' is of incorrect length")
    group_means = _group_means(x, codes, ng)
    scaling = np.zeros((p, p, ng), dtype=float)
    ldet = np.zeros(ng, dtype=float)
    methods = ("moment", "mle", "mve", "t")
    if method not in methods:
        raise MassError(f"'{method}' is not a valid method")
    if cv and method not in ("moment", "mle"):
        raise MassError(f"cannot use leave-one-out CV with method '{method}'")
    for i in range(ng):
        mask = codes == i
        if method == "mve":
            center, cov = _cov_mve(x[mask, :])
            group_means[i, :] = center
            u, s, vh = np.linalg.svd(cov, full_matrices=False)
            v = vh.T
            scaling[:, :, i] = v @ np.diag(np.sqrt(1.0 / s))
            ldet[i] = float(np.sum(np.log(s)))
        elif method == "t":
            if nu <= 2:
                raise MassError("'nu' must exceed 2")
            m = int(counts[i])
            xi = x[mask, :]
            w = np.ones(m, dtype=float)
            while True:
                w0 = w.copy()
                w_mat = _scale_center(xi, group_means[i, :])
                svd_input = math.sqrt((1.0 + p / nu) * w / m) * w_mat
                u, s, vh = np.linalg.svd(svd_input, full_matrices=False)
                v = vh.T
                w_mat = w_mat @ v @ np.diag(1.0 / s)
                w = 1.0 / (1.0 + (w_mat**2).sum(axis=1) / nu)
                group_means[i, :] = (w[:, None] * xi).sum(axis=0) / w.sum()
                if np.all(np.abs(w - w0) < 1e-2):
                    break
            qx_data = np.sqrt(w)[:, None] * _scale_center(xi, group_means[i, :])
            qx_mat, rank = _linpack_qr(qx_data)
            if rank < p:
                raise MassError(f"rank deficiency in group {lev[i]}")
            qx_mat = qx_mat * math.sqrt((1.0 + p / nu) / m)
            scaling[:, :, i] = _backsolve_upper(qx_mat[:p, :p], np.eye(p))
            ldet[i] = 2.0 * float(np.sum(np.log(np.abs(np.diag(qx_mat[:p, :p])))))
        else:
            nk = counts[i] - 1.0 if method == "moment" else counts[i]
            xi = _scale_center(x[mask, :], group_means[i, :]) / math.sqrt(nk)
            qx_mat, rank = _linpack_qr(xi)
            if rank < p:
                raise MassError(f"rank deficiency in group {lev[i]}")
            scaling[:, :, i] = _backsolve_upper(qx_mat[:p, :p], np.eye(p))
            ldet[i] = 2.0 * float(np.sum(np.log(np.abs(np.diag(qx_mat[:p, :p])))))
    if cv:
        ng_factor = 0 if method == "mle" else 1
        dist = np.zeros((n, ng), dtype=float)
        ldet_mat = np.zeros((n, ng), dtype=float)
        for i in range(ng):
            dev = (x - group_means[i, :]) @ scaling[:, :, i]
            dist[:, i] = np.sum(dev**2, axis=1)
            ldet_mat[:, i] = ldet[i]
        nc = counts[codes]
        ind_row = np.arange(n)
        ind_col = codes
        fac = 1.0 - nc / (nc - 1.0) / (nc - ng_factor) * dist[ind_row, ind_col]
        fac = np.maximum(fac, 1e-10)
        ldet_mat[ind_row, ind_col] = (
            np.log(fac) + p * np.log((nc - ng_factor) / (nc - 1.0 - ng_factor)) + ldet_mat[ind_row, ind_col]
        )
        dist[ind_row, ind_col] = (
            dist[ind_row, ind_col]
            * (nc**2 / (nc - 1.0) ** 2)
            * (nc - 1.0 - ng_factor)
            / (nc - ng_factor)
            / fac
        )
        dist = 0.5 * dist + 0.5 * ldet_mat - np.log(prior_arr)[None, :]
        dist = np.exp(-(dist - np.min(dist, axis=1, keepdims=True)))
        posterior = dist / dist.sum(axis=1, keepdims=True)
        class_idx = np.argmax(posterior, axis=1)
        class_ = lev[class_idx]
        return QdaCvResult(class_=class_, posterior=posterior)
    col_names = None
    if hasattr(x, "columns"):
        col_names = list(x.columns)
    elif x.dtype.names:
        col_names = list(x.dtype.names)
    res = QdaFit(
        prior=prior_arr,
        counts=counts,
        means=group_means,
        scaling=scaling,
        ldet=ldet,
        lev=lev,
        n=n,
        method=method,
    )
    return res


def _split_formula(formula: str) -> tuple[str, str]:
    if "~" not in formula:
        raise MassError("invalid formula")
    resp, rhs = formula.split("~", 1)
    return resp.strip(), rhs.strip()


def _parse_rhs_terms(rhs: str) -> tuple[bool, list[str]]:
    rhs = rhs.strip()
    intercept = True
    if rhs.startswith("0 +") or rhs.startswith("-1 +"):
        intercept = False
        rhs = rhs.split("+", 1)[1].strip()
    elif rhs.startswith("1 +"):
        rhs = rhs.split("+", 1)[1].strip()
    terms = [part.strip() for part in rhs.split("+") if part.strip()]
    return intercept, terms


def _model_matrix_qda(data: dict[str, Any], formula: str) -> tuple[np.ndarray, np.ndarray]:
    resp, rhs = _split_formula(formula)
    intercept, terms = _parse_rhs_terms(rhs)
    grouping = np.asarray(data[resp])
    n = grouping.shape[0]
    columns: list[np.ndarray] = []
    if intercept:
        columns.append(np.ones(n))
    for term in terms:
        if term not in data:
            raise MassError(f"object '{term}' not found")
        col = np.asarray(data[term], dtype=float).reshape(-1)
        if col.shape[0] != n:
            raise MassError(f"column '{term}' has length {col.shape[0]}, not {n}")
        columns.append(col)
    x = np.column_stack(columns)
    if intercept:
        x = x[:, 1:]
    return x, grouping


def qda(
    x,
    grouping=None,
    *,
    prior=_PRIOR_PROPORTIONS,
    method: str = "moment",
    CV: bool = False,
    nu: float = 5.0,
    data: dict[str, Any] | None = None,
    subset=None,
    na_action: Callable | None = None,
    **kwargs: Any,
) -> QdaFit | QdaCvResult:
    """Quadratic discriminant analysis."""
    if kwargs:
        pass
    if isinstance(x, str):
        if data is None:
            raise TypeError("formula qda requires data=")
        mat, grp = _model_matrix_qda(data, x)
        res = _qda_default(mat, grp, prior=prior, method=method, cv=CV, nu=nu)
        if isinstance(res, QdaFit):
            res.terms = x
        return res
    if isinstance(x, dict):
        mat = np.column_stack([np.asarray(x[key], dtype=float).reshape(-1) for key in x])
        return qda(mat, grouping, prior=prior, method=method, CV=CV, nu=nu, subset=subset, na_action=na_action)
    mat = np.asarray(x, dtype=float)
    if grouping is None:
        raise TypeError("grouping is required for matrix qda")
    grp = grouping
    if subset is not None:
        mat = mat[subset, :]
        grp = np.asarray(grp)[subset]
    if na_action is not None:
        frame_g = np.asarray(grp)
        frame_x = mat
        # minimal na.omit-style for numeric x
        ok = np.all(np.isfinite(frame_x), axis=1)
        if not np.all(ok):
            frame_g = frame_g[ok]
            frame_x = frame_x[ok]
        grp = frame_g
        mat = frame_x
    return _qda_default(mat, grp, prior=prior, method=method, cv=CV, nu=nu)


def qda_values(fit: QdaFit) -> np.ndarray:
    """Flat numeric vector of prior, means, scaling, and ldet for checks."""
    return np.concatenate(
        [
            np.asarray(fit.prior, dtype=float).reshape(-1, order="F"),
            np.asarray(fit.means, dtype=float).reshape(-1, order="F"),
            np.asarray(fit.scaling, dtype=float).reshape(-1, order="F"),
            np.asarray(fit.ldet, dtype=float).reshape(-1, order="F"),
        ]
    )
