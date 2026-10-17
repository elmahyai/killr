"""Rank, null space, and the angle between subspaces."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.linalg_internal import (
    _EPS,
    column_vector,
    ensure_matrix,
    is_numeric,
    is_vector,
    length,
    linpack_q,
    linpack_qr,
    svd_full,
)


def _as_rank_matrix(M):
    if not is_numeric(M):
        raise PracmaError("Argument 'M' must be a numeric matrix.")
    if is_vector(M):
        return column_vector(M)
    return np.array(M, dtype=float, copy=True)


def Rank(M):
    if length(M) == 0:
        return np.array([0.0])
    matrix = _as_rank_matrix(M)
    _, _, _, qr_rank = linpack_qr(matrix)
    _, sigma, _ = svd_full(matrix)
    if sigma.size == 0:
        svd_rank = 0
    else:
        tol = max(matrix.shape) * float(np.max(sigma)) * _EPS
        svd_rank = int(np.sum(sigma > tol))
    if qr_rank != svd_rank:
        warnings.warn("Rank calculation may be problematic.", stacklevel=2)
    return np.array([float(svd_rank)])


def nullspace(M):
    if not is_numeric(M):
        raise PracmaError("Argument 'M' must be a numeric matrix.")
    matrix = column_vector(M) if is_vector(M) else np.array(M, dtype=float, copy=True)
    factors, qraux, _, rank = linpack_qr(matrix.T)
    if rank == matrix.shape[1]:
        return None
    q = linpack_q(factors, qraux, rank)
    basis = q if rank == 0 else q[:, rank:]
    if basis.size == 0:
        return None
    return basis


null = nullspace


def orth(M):
    if length(M) == 0:
        return None
    if not is_numeric(M):
        raise PracmaError("Argument 'M' must be a numeric matrix.")
    matrix = column_vector(M) if is_vector(M) else np.array(M, dtype=float, copy=True)
    u, singular, _ = svd_full(matrix)
    if singular.size == 0 or float(np.max(singular)) == 0 and singular.size:
        tol = 0.0
        rank = 0
    else:
        tol = max(matrix.shape) * float(np.max(singular)) * _EPS
        rank = int(np.sum(singular > tol))
    # R's U[, 1:0] is c(1, 0), and a zero subscript is dropped, leaving column 1.
    if rank == 0:
        return u[:, :1] if u.shape[1] else u
    return u[:, :rank]


def subspace(A, B):
    if not is_numeric(A) or not is_numeric(B):
        raise PracmaError("Arguments 'A' and 'B' must be numeric matrices.")
    left = column_vector(A) if is_vector(A) else np.array(A, dtype=float, copy=True)
    right = column_vector(B) if is_vector(B) else np.array(B, dtype=float, copy=True)
    if left.shape[0] != right.shape[0]:
        raise PracmaError("Matrices 'A' and 'B' must have the same number of rows.")
    left = orth(left)
    right = orth(right)
    if left.shape[1] < right.shape[1]:
        left, right = right, left
    for k in range(left.shape[1]):
        column = left[:, k : k + 1]
        right = right - column @ (column.T @ right)
    _, singular, _ = svd_full(right)
    peak = 0.0 if singular.size == 0 else float(np.max(singular))
    return float(np.arcsin(min(1.0, peak)))
