"""Linear and affine projection."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Norm
from pracma.num_helpers import column_matrix, is_r_numeric, qr_solve, r_rank, r_svd


def linearproj(A, B):
    if not is_r_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_r_numeric(B):
        raise PracmaError("is.numeric(B) is not TRUE")
    basis = column_matrix(A)
    points = column_matrix(B)
    if basis.shape[0] != points.shape[0]:
        raise PracmaError("Arguments 'A', 'B' must have the same number of rows.")
    if r_rank(basis) < basis.shape[1]:
        raise PracmaError("Matrix 'A' does not have maximal rank -- not a basis.")
    gram = basis.T @ basis
    coeff = qr_solve(gram, basis.T @ points)
    if coeff.ndim == 1:
        coeff = coeff.reshape(-1, 1)
    return {"P": coeff, "Q": basis @ coeff}


def affineproj(x0, C, b, unbound=True, maxniter=100):
    point = np.asarray(x0, dtype=float).reshape(-1)
    constraint = np.asarray(C, dtype=float)
    if constraint.ndim == 1:
        constraint = constraint.reshape(1, -1)
    target = np.asarray(b, dtype=float).reshape(-1)
    if unbound:
        width = constraint.shape[1]
        gram = constraint @ constraint.T
        correction = qr_solve(gram, constraint)
        if correction.ndim == 1:
            correction = correction.reshape(-1, 1)
        shift = qr_solve(gram, target)
        projected = (np.eye(width) - constraint.T @ correction) @ point + constraint.T @ shift
        return {
            "proj": np.asarray(projected, dtype=float).reshape(-1, 1),
            "dist": float(Norm(projected)),
            "niter": 0,
        }
    u, singular, v = r_svd(constraint)
    factor = v @ np.diag(1.0 / singular) @ u.T
    current = point.copy()
    iterate = True
    niter = 0
    while iterate and niter <= maxniter:
        niter += 1
        residual = target - (constraint @ current)
        current = current + (factor @ residual).reshape(-1)
        if np.any(current < 0):
            current[current < 0] = 0.0
        else:
            iterate = False
    return {"proj": current, "dist": float(Norm(point - current)), "niter": int(niter)}
