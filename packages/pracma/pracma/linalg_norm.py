"""Norm estimates, positive definiteness, and the nearest SPD matrix."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.elementary import eps
from pracma.linalg_internal import (
    _EPS,
    column_vector,
    frobenius,
    is_matrix,
    is_numeric,
    is_vector,
    length,
)


def normest(M, maxiter=100, tol=float(np.finfo(float).eps) ** 0.5):
    if length(M) == 0:
        return np.array([0.0])
    if not is_numeric(M):
        raise PracmaError("Argument 'M' must be a numeric matrix.")
    matrix = column_vector(M) if is_vector(M) else np.array(M, dtype=float, copy=False)
    x = np.sum(np.abs(matrix), axis=0).reshape(-1, 1)
    est = frobenius(x)
    if est == 0:
        return np.array([0.0])
    x = x / est
    est0 = 0.0
    niter = 0
    while abs(est - est0) > tol * est and niter <= maxiter:
        est0 = est
        mx = matrix @ x
        if np.all(mx == 0):
            mx = np.random.random(mx.shape)
        x = matrix.T @ mx
        normx = frobenius(x)
        est = normx / frobenius(mx)
        x = x / normx
        niter += 1
    if niter > maxiter:
        warnings.warn("Number of iterations exceeded 'maxiter'.", stacklevel=2)
    return np.array([float(est)])


def fnorm(f, g, x1, x2, p=2, npoints=100):
    from pracma.arrays import Norm
    from pracma.linalg_internal import stopifnot

    stopifnot(
        [
            ("is.numeric(x1)", is_numeric(x1)),
            ("length(x1) == 1", length(x1) == 1),
            ("is.numeric(x2)", is_numeric(x2)),
            ("length(x2) == 1", length(x2) == 1),
            ("x1 < x2", float(np.asarray(x1)) < float(np.asarray(x2))),
            ("is.numeric(npoints)", is_numeric(npoints)),
            ("length(npoints) == 1", length(npoints) == 1),
            ("npoints >= 2", float(np.asarray(npoints)) >= 2),
        ]
    )
    grid = np.linspace(float(np.asarray(x1)), float(np.asarray(x2)), int(np.asarray(npoints)))
    left = np.asarray(f(grid), dtype=float).reshape(-1)
    right = np.asarray(g(grid), dtype=float).reshape(-1)
    if left.size != grid.size or right.size != grid.size:
        raise PracmaError("Arguments 'f' and 'g' must be vectorized functions.")
    return np.array([Norm(left - right, p=p)])


def nearest_spd(A):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    machine = _EPS
    matrix = np.array(A, dtype=float, copy=False)
    m, n = matrix.shape
    if m != n:
        raise PracmaError("Argument 'A' must be a square matrix.")
    if n == 1 and matrix[0, 0] <= 0:
        return np.array([[machine]])
    symmetric = (matrix + matrix.T) / 2
    _, singular, v = np.linalg.svd(symmetric, full_matrices=True)
    # H = V diag(d) V^T. numpy returns Vh, so V = Vh.T.
    polar = v.T @ np.diag(singular) @ v
    estimate = (symmetric + polar) / 2
    estimate = (estimate + estimate.T) / 2
    k = 0
    not_pd = True
    while not_pd:
        k += 1
        try:
            np.linalg.cholesky(estimate)
            not_pd = False
        except np.linalg.LinAlgError:
            values = np.linalg.eigvalsh(estimate)
            mineig = float(np.min(values))
            # A local numeric named eps does not hide the pracma function call.
            estimate = estimate + (-mineig * k**2 + float(eps(mineig))) * np.eye(n)
    return estimate


def isposdef(A, psd=False, tol=1e-10):
    matrix = np.array(A, dtype=float, copy=False)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        warnings.warn("Matrix 'A' is not quadratic.\n", stacklevel=2)
        return False
    if np.any(np.abs(matrix - matrix.T) > tol):
        warnings.warn("Matrix 'A' is not symmetric.\n", stacklevel=2)
        return False
    if not psd:
        try:
            np.linalg.cholesky(matrix)
            return True
        except np.linalg.LinAlgError:
            return False
    return _chol_pivot_ok(matrix)


def _chol_pivot_ok(matrix):
    """Pivoted Cholesky. R's chol(pivot=TRUE) succeeds for semidefinite matrices."""
    n = matrix.shape[0]
    work = np.array(matrix, dtype=float, copy=True)
    tol = n * _EPS * max(1.0, float(np.max(np.abs(np.diag(work)))) if n else 0.0)
    for k in range(n):
        pivot = k + int(np.argmax(np.diag(work)[k:]))
        if work[pivot, pivot] < tol:
            return True
        if pivot != k:
            work[[k, pivot], :] = work[[pivot, k], :]
            work[:, [k, pivot]] = work[:, [pivot, k]]
        work[k, k] = math_sqrt(work[k, k])
        if k + 1 < n:
            work[k, k + 1 :] = work[k, k + 1 :] / work[k, k]
            work[k + 1 :, k + 1 :] -= np.outer(work[k, k + 1 :], work[k, k + 1 :])
    return True


def math_sqrt(value):
    return float(np.sqrt(value))
