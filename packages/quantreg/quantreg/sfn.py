"""rq.fit.sfn: the sparse Frisch-Newton fit on a scipy.sparse design.

The R version takes a SparseM matrix.csr. Here the design is any scipy.sparse
matrix (or a dense array, which is converted), in place of SparseM. The loop
is the Rust kernel `srqfn` in crates/quantreg, which the R `.Fortran("srqfn")`
call runs. This module does the R-level steps around it: the sign flip, the
starting point from the least-squares dual, the slacks, and the result.
"""

from __future__ import annotations

import warnings

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

import quantreg_kernel as _k
import quantreg_sfnc_kernel as _kc
from quantreg.messages import sfn_control, sfn_message


def _design(a):
    design = sp.csr_matrix(a, dtype=float)
    design.sum_duplicates()
    design.sort_indices()
    return design


def rq_fit_sfnc(x, y, R, r, tau=0.5, rhs=None, control=None):
    """rq.fit.sfnc(x, y, R, r, tau, rhs, control): the constrained sparse fit.

    The R version takes SparseM matrix.csr objects for x and R. Here x and R are any
    scipy.sparse matrices (or dense arrays), in place of SparseM. The constraints are
    R b >= r. The loop is the Rust kernel `srqfnc` in crates/quantreg_sfnc, which the R
    `.Fortran("srqfnc")` call runs. This function does the R-level steps around it:
    the sign flip, the starting point from the least-squares dual, the slacks, and the
    result. Returns the fields the R function returns: coefficients, residuals,
    control, ierr and it.
    """
    design = _design(x)
    constraints = _design(R)
    n1, m = design.shape
    n2 = constraints.shape[0]
    y = np.asarray(y, dtype=float).reshape(-1)
    r = np.asarray(r, dtype=float).reshape(-1)
    if n1 != y.shape[0]:
        raise ValueError("The design matrix A1' and response vector y are not compatible")
    if n2 != r.shape[0]:
        raise ValueError("The constraint matrix A2' and constraint rhs are not compatible")
    if constraints.shape[1] != m:
        raise ValueError("R and x have different numbers of columns")
    tau = float(tau)
    ctrl = sfn_control()
    if control is not None:
        ctrl.update(dict(control))
    ctrl["maxiter"] = int(ctrl["maxiter"])
    y = -y
    r = -r
    if rhs is None:
        rhs = (1.0 - tau) * np.asarray(design.sum(axis=0), dtype=float).reshape(-1)
    rhs = np.ascontiguousarray(np.asarray(rhs, dtype=float).reshape(-1))

    x1 = np.full(n1, 1.0 - tau)
    x2 = np.ones(n2)
    s = np.ones(n1) - x1
    z2 = np.ones(n2)
    # starting dual: least squares b0 = (A1'A1)^{-1} A1'y, as chol(e) in R
    ao = design.T.tocsr()
    e = (ao @ design).tocsc()
    b0 = np.asarray(spsolve(e, ao @ y), dtype=float).reshape(-1)
    r1 = y - design @ b0
    small = float(ctrl["small"])
    z1 = np.where(np.abs(r1) < small, r1 * (r1 > 0) + small, r1 * (r1 > 0))
    w = z1 - r1

    sol, it, ierr = _kc.sfnc(
        n1,
        n2,
        m,
        design.indptr.astype(np.int64),
        design.indices.astype(np.int64),
        np.ascontiguousarray(design.data, dtype=float),
        constraints.indptr.astype(np.int64),
        constraints.indices.astype(np.int64),
        np.ascontiguousarray(constraints.data, dtype=float),
        rhs,
        np.ascontiguousarray(r),
        np.ascontiguousarray(x1),
        np.ascontiguousarray(x2),
        np.ascontiguousarray(s),
        np.ascontiguousarray(z1),
        np.ascontiguousarray(z2),
        np.ascontiguousarray(w),
        np.ascontiguousarray(b0),
        small,
        float(ctrl["tiny"]),
        float(ctrl["Large"]),
        int(ctrl["maxiter"]),
    )
    ierr = int(ierr)
    if ierr != 0 and ctrl.get("warn.mesg", True):
        warnings.warn(sfn_message(ierr) or f"sfnc error {ierr}")
    coefficients = -np.asarray(sol, dtype=float)
    residuals = -y - design @ coefficients
    return {
        "coefficients": coefficients,
        "residuals": residuals,
        "control": ctrl,
        "ierr": ierr,
        "it": int(it),
    }


def rq_fit_sfn(a, y, tau=0.5, rhs=None, control=None):
    """rq.fit.sfn(a, y, tau, rhs, control).

    Returns a dict with `coefficients`, `residuals`, `control`, `ierr` and `it`,
    the fields the R function returns.
    """
    design = _design(a)
    n, m = design.shape
    y = np.asarray(y, dtype=float).reshape(-1)
    if n != y.shape[0]:
        raise ValueError("Dimensions of design matrix and the response vector not compatible")
    tau = float(tau)
    ctrl = sfn_control()
    if control is not None:
        ctrl.update(dict(control))
    ctrl["maxiter"] = int(ctrl["maxiter"])
    y = -y
    if rhs is None:
        rhs = (1.0 - tau) * np.asarray(design.sum(axis=0), dtype=float).reshape(-1)
    rhs = np.ascontiguousarray(np.asarray(rhs, dtype=float).reshape(-1))

    x = np.full(n, 1.0 - tau)
    s = np.ones(n) - x
    # starting dual: least squares b1 = (A'A)^{-1} A'y, as solve(e, ao %*% y) in R
    ao = design.T.tocsr()
    e = (ao @ design).tocsc()
    b1 = np.asarray(spsolve(e, ao @ y), dtype=float).reshape(-1)
    r = y - design @ b1
    small = float(ctrl["small"])
    z = np.where(np.abs(r) < small, r * (r > 0) + small, r * (r > 0))
    w = z - r

    indptr = design.indptr.astype(np.int64)
    indices = design.indices.astype(np.int64)
    data = np.ascontiguousarray(design.data, dtype=float)
    sol, it, ierr = _k.sfn(
        n,
        m,
        indptr,
        indices,
        data,
        rhs,
        np.ascontiguousarray(x),
        np.ascontiguousarray(s),
        np.ascontiguousarray(b1),
        np.ascontiguousarray(z),
        np.ascontiguousarray(w),
        small,
        float(ctrl["tiny"]),
        float(ctrl["Large"]),
        int(ctrl["maxiter"]),
    )
    ierr = int(ierr)
    if ierr != 0 and ctrl.get("warn.mesg", True):
        warnings.warn(sfn_message(ierr) or f"sfn error {ierr}")
    coefficients = -np.asarray(sol, dtype=float)
    residuals = -y - design @ coefficients
    return {
        "coefficients": coefficients,
        "residuals": residuals,
        "control": ctrl,
        "ierr": ierr,
        "it": int(it),
    }
