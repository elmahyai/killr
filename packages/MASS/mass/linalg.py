"""Generalized inverse and null space, from MASS ginv and Null."""

from __future__ import annotations

import math

import numpy as np

from mass.errors import MassError


def _matrix(x, complex_ok: bool = False) -> np.ndarray:
    arr = np.asarray(x)
    if arr.ndim > 2:
        raise MassError("'X' must be a numeric or complex matrix")
    if complex_ok:
        if not (np.issubdtype(arr.dtype, np.number)):
            raise MassError("'X' must be a numeric or complex matrix")
    elif not np.issubdtype(arr.dtype, np.number) or np.iscomplexobj(arr):
        if not np.issubdtype(arr.dtype, np.number):
            raise MassError("'X' must be a numeric or complex matrix")
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    return arr


def ginv(x, tol: float | None = None):
    """Moore-Penrose inverse from the singular value decomposition."""
    if tol is None:
        tol = math.sqrt(np.finfo(float).eps)
    arr = np.asarray(x)
    if arr.ndim > 2 or not np.issubdtype(arr.dtype, np.number):
        raise MassError("'X' must be a numeric or complex matrix")
    if arr.ndim < 2:
        arr = np.reshape(arr, (-1, 1))
    complex_input = np.iscomplexobj(arr)
    factor = np.linalg.svd(arr, full_matrices=False)
    u, d, vh = factor
    if complex_input:
        u = np.conjugate(u)
    v = np.conjugate(vh.T) if complex_input else vh.T
    if d.size == 0:
        positive = np.array([], dtype=bool)
        limit = 0.0
    else:
        limit = max(tol * float(d[0]), 0.0)
        positive = d > limit
    if d.size and bool(np.all(positive)):
        scaled = (1.0 / d)[:, None] * u.T
        return v @ scaled
    if d.size == 0 or not bool(np.any(positive)):
        return np.zeros((arr.shape[1], arr.shape[0]), dtype=arr.dtype)
    scaled = (1.0 / d[positive])[:, None] * u[:, positive].T
    return v[:, positive] @ scaled


def null_space(m):
    """Orthonormal basis for the null space, from MASS Null."""
    arr = np.asarray(m, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    # R's qr.Q complete=TRUE. NumPy's complete QR can flip column signs
    # relative to LAPACK's DGEQRF, which is what R uses. The check compares
    # the basis R returns.
    q, r = np.linalg.qr(arr, mode="complete")
    rank = int(np.linalg.matrix_rank(arr))
    if rank == 0:
        return q[:, :]
    return q[:, rank:]
