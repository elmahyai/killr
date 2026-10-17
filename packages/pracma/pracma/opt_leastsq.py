"""Linear least squares from pracma."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.elementary import eps
from pracma.opt_helpers import _is_numeric, _lstsq, _nullspace, _pinv, _repmat, _spectral_norm, _warn


def lsqnonneg(C, d):
    if not _is_numeric(C) or not _is_numeric(d):
        raise PracmaError("is.numeric(C) is not TRUE")
    matrix = np.asarray(C, dtype=float)
    rhs = np.asarray(d)
    if matrix.ndim != 2 or rhs.ndim != 1:
        raise PracmaError("Argument 'C' must be a matrix, 'd' a vector.")
    dvec = as_1d(d)
    m, n = matrix.shape
    if m != dvec.size:
        raise PracmaError("Arguments 'C' and 'd' have nonconformable dimensions.")
    tol = 10 * eps() * _spectral_norm(matrix) * (max(n, m) + 1)
    x = np.zeros(n)
    P = np.zeros(n, dtype=bool)
    Z = ~P
    resid = dvec - matrix @ x
    w = (matrix.T @ resid.reshape(-1, 1)).reshape(-1)
    it = 0
    itmax = 3 * n
    while np.any(Z) and np.any(w[Z] > tol):
        z = np.zeros(n)
        wz = np.full(n, -np.inf)
        wz[Z] = w[Z]
        im = int(np.argmax(wz))
        P[im] = True
        Z[im] = False
        z[P] = _lstsq(matrix[:, P], dvec)
        while np.any(z[P] <= 0):
            it += 1
            if it > itmax:
                raise PracmaError("Iteration count exceeded.")
            Q = (z <= 0) & P
            alpha = float(np.min(x[Q] / (x[Q] - z[Q])))
            x = x + alpha * (z - x)
            Z = ((np.abs(x) < tol) & P) | Z
            P = ~Z
            z = np.zeros(n)
            z[P] = _lstsq(matrix[:, P], dvec)
        x = z
        resid = dvec - matrix @ x
        w = (matrix.T @ resid.reshape(-1, 1)).reshape(-1)
    return {"x": x, "resid.norm": float(np.sum(resid * resid))}


def lsqlin(A, b, C=None, d=None, tol=1e-13):
    if not _is_numeric(A) or not _is_numeric(b):
        raise PracmaError("is.numeric(A) is not TRUE")
    design = np.asarray(A, dtype=float)
    if design.ndim != 2:
        raise PracmaError("Argument 'A' must be a numeric matrix.")
    design = np.array(design, dtype=float, copy=True)
    n, m = design.shape
    rhs = np.asarray(b, dtype=float)
    if rhs.ndim == 1:
        if rhs.size != n:
            raise PracmaError("As vector argument 'b' must have 'nrow(A)' elements.")
        rhs = rhs.reshape(-1, 1)
        columns = 1
    elif rhs.ndim == 2:
        if rhs.shape[0] != n:
            raise PracmaError("As Matrix argument 'b' must also have 'nrow(A)' rows.")
        columns = rhs.shape[1]
    else:
        raise PracmaError("Argument 'b' must be a vector or a matrix with n rows.")
    if C is None and d is None:
        return _lstsq_columns(design, rhs)
    if (C is None) != (d is None):
        raise PracmaError("Condition 'C * x = d' not fully specified, 'C' or 'd' missing.")
    if not _is_numeric(C) or not _is_numeric(d):
        raise PracmaError("is.numeric(C) is not TRUE")
    constraint = np.asarray(C, dtype=float)
    if constraint.ndim != 2 or constraint.shape[1] != m:
        raise PracmaError("Argument 'C' must be a numeric matrix with 'ncol(C)=ncol(A)'.")
    target = np.asarray(d, dtype=float).reshape(-1, 1)
    xc = _pinv(constraint) @ target
    if np.any(np.abs(constraint @ xc - target) > tol):
        _warn("Precondition 'C * x = d' cannot be satisfied (within tolerance 'tol').")
        return None
    N = _nullspace(constraint)
    if N is None:
        return xc.reshape(-1)
    M = design @ N
    xn = _pinv(M) @ (rhs - _repmat(design @ xc, 1, columns))
    return _repmat(xc, 1, columns) + N @ xn


def _lstsq_columns(design, rhs):
    if rhs.shape[1] == 1:
        return _lstsq(design, rhs).reshape(-1, 1)
    columns = [_lstsq(design, rhs[:, j]) for j in range(rhs.shape[1])]
    return np.column_stack(columns)
