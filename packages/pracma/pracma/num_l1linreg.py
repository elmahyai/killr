"""Iteratively reweighted L1 linear regression."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import column_matrix, is_r_numeric, qr_solve


def L1linreg(A, b, p=1, tol=1e-07, maxiter=200):
    if not is_r_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_r_numeric(b):
        raise PracmaError("is.numeric(b) is not TRUE")
    design = column_matrix(A)
    rows = design.shape[0]
    target = np.asarray(b, dtype=float).reshape(-1)
    if target.size != rows:
        raise PracmaError("Arguments 'A' and 'b' are not compatible.")
    if p > 1:
        raise PracmaError("Argument 'p' must be smaller or equal to 1.")
    coeff = qr_solve(design, target)
    previous = coeff.copy()
    previous[0] = previous[0] + 10 * tol
    iteration = 1
    while np.max(np.abs(coeff - previous)) > tol and iteration <= maxiter:
        previous = coeff.copy()
        residual = np.maximum(np.abs(design @ previous - target), tol)
        if p == 1:
            weight = np.sqrt(1.0 / residual)
        else:
            weight = np.sqrt(residual ** (p - 2))
        coeff = qr_solve(weight[:, None] * design, weight * target)
        iteration += 1
    if iteration > maxiter:
        warnings.warn("Reached max. no. of iterations; may not have converged.", stacklevel=2)
    return {"x": coeff, "reltol": float(np.max(np.abs(coeff - previous))), "niter": int(iteration)}
