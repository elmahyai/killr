"""Linear and quadratic programs from pracma."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.opt_helpers import _inf_norm, _is_numeric, _solve, _warn


def _as_matrix(value):
    array = np.asarray(value, dtype=float)
    if array.ndim == 1:
        return array.reshape(1, -1)
    return np.array(array, dtype=float, copy=True)


def quadprog(C, d, A=None, b=None, Aeq=None, beq=None, lb=None, ub=None):
    raise PracmaError("quadprog needed for this function to work. Please install it.")


def lsqlincon(C, d, A=None, b=None, Aeq=None, beq=None, lb=None, ub=None):
    raise PracmaError("quadprog needed for this function to work. Please install it.")


def fmincon(x0, fn, gr=None, *args, method="SQP", A=None, b=None, Aeq=None, beq=None,
            lb=None, ub=None, hin=None, heq=None, tol=1e-06, maxfeval=10000, maxiter=5000, **kwargs):
    if method != "SQP":
        raise PracmaError("Methods other than 'SQP' are not yet implemented.")
    point = as_1d(x0) if _is_numeric(x0) else np.asarray([])
    if not _is_numeric(x0) or point.size <= 1:
        raise PracmaError("'x0' must be a numeric vector of length greater 1.")
    if gr is not None:
        _warn("Gradient function is not used for SQP approach.")
    raise PracmaError("Package 'NlcOptim' missing -- install from CRAN.")


def _lp_check(cc, A, b, lb, ub):
    if not _is_numeric(cc):
        raise PracmaError("is.numeric(cc) is not TRUE")
    if (_is_numeric(lb) and as_1d(lb).size != as_1d(cc).size) or (
        _is_numeric(ub) and as_1d(ub).size != as_1d(cc).size
    ):
        raise PracmaError("Arguments 'cc', 'lb', and 'ub' must have equal lengths.")
    if A is not None:
        if b is None:
            raise PracmaError("Vector 'b' must be present if 'A' is.")
        matrix = np.asarray(A, dtype=float)
        if matrix.ndim != 2:
            raise PracmaError("Argument 'A' must be a matrix.")
        if as_1d(cc).size != matrix.shape[1]:
            raise PracmaError("Length of 'cc' does not fit to 'ncol(A)'.")
        if as_1d(b).size != matrix.shape[0]:
            raise PracmaError("Length of 'b' does not fit to 'nrow(A)'.")


def _lp_create(cc, Ain, bin, lb, ub):
    cost = as_1d(cc)
    if Ain is None:
        A = None
        b = np.array([])
        n = cost.size
    else:
        A = np.array(Ain, dtype=float, copy=True)
        b = as_1d(bin)
        n = A.shape[1]
    if ub is not None:
        upper = as_1d(ub)
        inds = np.flatnonzero(np.isfinite(upper))
        if inds.size:
            B = np.zeros((inds.size, n))
            for k, index in enumerate(inds):
                B[k, index] = 1
            A = B if A is None else np.vstack([A, B])
            b = np.concatenate([b, upper[inds]])
    if lb is not None:
        lower = as_1d(lb)
        inds = np.flatnonzero(lower > 0)
        if inds.size:
            B = np.zeros((inds.size, n))
            for k, index in enumerate(inds):
                B[k, index] = -1
            A = B if A is None else np.vstack([A, B])
            b = np.concatenate([b, -lower[inds]])
    m = A.shape[0]
    A = np.hstack([A, np.eye(m)])
    cost = np.concatenate([cost, np.zeros(m)])
    v = np.concatenate([np.zeros(n), b])
    I = list(range(n, n + m))
    return {"A": A, "b": b, "cc": cost, "x0": v, "I0": I}


def _lp_solve(cc, A, b, x, I, maxiter=20):
    if not _is_numeric(A) or not _is_numeric(b) or not _is_numeric(x):
        raise PracmaError("is.numeric(A) is not TRUE")
    matrix = np.asarray(A, dtype=float)
    if matrix.ndim != 2:
        raise PracmaError("Argument 'A' must be a numeric matrix.")
    rhs = as_1d(b)
    point = as_1d(x)
    cost = as_1d(cc)
    m, n = matrix.shape
    if rhs.size != m or point.size != n:
        raise PracmaError("One of arguments 'x' or 'b' does not have correct length.")
    basis = list(I)
    iteration = 0
    errno = 0
    y = None
    while iteration < maxiter:
        iteration += 1
        free = [j for j in range(n) if j not in basis]
        B = matrix[:, basis]
        y = _solve(B.T, cost[basis])
        u = np.zeros(n)
        for j in free:
            u[j] = cost[j] - float(matrix[:, j] @ y)
        if np.all(u >= 0):
            errno = 1
            break
        negative = np.flatnonzero(u < 0)
        r = int(negative[0])
        dd = _solve(B, matrix[:, r])
        d = np.zeros(n)
        d[basis] = dd
        if np.all(d <= 0):
            errno = -2
            break
        i0 = np.flatnonzero(d > 0)
        ratios = point[i0] / d[i0]
        t = float(np.min(ratios))
        s_candidates = i0[np.flatnonzero(ratios == t)]
        s = int(s_candidates[0])
        z = np.zeros(n)
        z[r] = t
        z[np.array(basis)] = point[np.array(basis)] - t * d[np.array(basis)]
        point = z
        basis[basis.index(s)] = r
    if iteration >= maxiter:
        errno = -1
    if errno < 0:
        point = np.nan
        y = np.nan
    return {"x": point, "dual.x": y, "errno": errno}


def linprog(cc, A=None, b=None, Aeq=None, beq=None, lb=None, ub=None, x0=None, I0=None,
            bigM=100, maxiter=20, maximize=False):
    _lp_check(cc, A, b, lb, ub)
    cost = as_1d(cc)
    if maximize:
        cost = -cost
    original = cost.copy()
    inequalities = None if A is None else np.array(A, dtype=float, copy=True)
    rhs = None if b is None else as_1d(b)
    if Aeq is None and rhs is not None and np.all(rhs >= 0):
        Pin = _lp_create(cost, inequalities, rhs, lb, ub)
        Sin = _lp_solve(Pin["cc"], Pin["A"], Pin["b"], Pin["x0"], Pin["I0"], maxiter=maxiter)
    elif Aeq is None and (rhs is None or np.all(np.asarray(rhs) >= 0)):
        Pin = _lp_create(cost, inequalities, np.array([]) if rhs is None else rhs, lb, ub)
        Sin = _lp_solve(Pin["cc"], Pin["A"], Pin["b"], Pin["x0"], Pin["I0"], maxiter=maxiter)
    else:
        if inequalities is None and lb is None and ub is None:
            matrix = np.array(Aeq, dtype=float, copy=True)
            rhs = as_1d(beq)
            cc0 = cost
        else:
            Pin = _lp_create(cost, inequalities, np.array([]) if rhs is None else rhs, lb, ub)
            Ain, bin, cc0 = Pin["A"], Pin["b"], Pin["cc"]
            if Aeq is not None:
                equal = np.array(Aeq, dtype=float, copy=True)
                pad = Ain.shape[1] - equal.shape[1]
                equal = np.hstack([equal, np.zeros((equal.shape[0], pad))])
                matrix = np.vstack([Ain, equal])
                rhs = np.concatenate([bin, as_1d(beq)])
            else:
                matrix, rhs = Ain, bin
        negative = np.flatnonzero(rhs < 0)
        if negative.size:
            matrix[negative, :] *= -1
            rhs[negative] *= -1
        m, n = matrix.shape
        A0 = np.hstack([matrix, np.eye(m)])
        b0 = rhs
        x_start = np.concatenate([np.zeros(n), b0])
        I_start = list(range(n, n + m))
        if bigM > 0:
            M = float(bigM)
            k = 1
            kmax = 8
            Sin = None
            while k < kmax:
                f = np.concatenate([cc0, np.full(m, M)])
                Sin = _lp_solve(f, A0, b0, x_start, I_start, maxiter=maxiter)
                slacks = np.asarray(Sin["x"])[I_start] if np.ndim(Sin["x"]) else np.array([np.nan])
                if Sin["errno"] < 0 or np.all(slacks == 0):
                    break
                M = 10 * M
                k += 1
            if k >= kmax:
                Sin["errno"] = -4
        else:
            f = np.ones(n + m)
            Sin = _lp_solve(f, A0, b0, x_start, I_start, maxiter=maxiter)
            if Sin["errno"] < 0:
                Sin["errno"] = -5
            else:
                phase = as_1d(Sin["x"])
                x1, z1 = phase[:n], phase[n : n + m]
                I1 = list(np.flatnonzero(x1 != 0))
                if len(I1) != m:
                    Sin["errno"] = -5
                elif np.all(z1 == 0):
                    Sin = _lp_solve(cc0, matrix, rhs, x1, I1, maxiter=maxiter)
                else:
                    Sin["errno"] = -2
    errno = Sin["errno"]
    errmsg = [
        "Maximum no. of iterations exceeded.",
        "Problem is most likely unfeasible.",
        "Problem is most likely unbounded.",
        "Big-M appraoch not successful.",
        "Phase-I approach not successful.",
    ]
    if errno < 0:
        return {"x": np.nan, "fval": np.nan, "errno": errno, "message": errmsg[abs(errno) - 1]}
    solution = as_1d(Sin["x"])[: original.size]
    value = float(np.sum(original * solution))
    if maximize:
        value = -value
    return {"x": solution, "fval": value, "errno": errno, "message": "Solver LP converged successfully."}


def qpspecial(G, x=None, maxit=100):
    if not _is_numeric(G):
        raise PracmaError("is.numeric(G) is not TRUE")
    matrix = np.asarray(G, dtype=float)
    if matrix.ndim != 2:
        raise PracmaError("is.matrix(G) is not TRUE")
    m, n = matrix.shape
    if m * n <= 0:
        _warn("qpspecial: Matrix 'G' is empty; nothing can be done.")
        return {"x": None, "d": None, "q": np.inf, "niter": 0, "info": 2}
    maxit = max(math.floor(float(maxit)), 5)
    e = np.ones(n)
    if x is None:
        point = e.copy()
    else:
        point = as_1d(x)
        if np.any(point < 0) or point.size != n:
            point = e.copy()
    Q = matrix.T @ matrix
    z = point.copy()
    y = 0.0
    eta = 0.9995
    delta = 3
    mu0 = float(np.sum(point * z) / n)
    tolmu = 1e-5
    tolrs = 1e-5
    kmu = tolmu * mu0
    nQ = _inf_norm(Q) + 2
    krs = tolrs * nQ
    info = 1
    k = 0
    for k in range(1, maxit + 1):
        r1 = -Q @ point + e * y + z
        r2 = -1 + float(np.sum(point))
        r3 = -point * z
        rs = max(float(np.max(np.abs(r1))), abs(r2))
        mu = -float(np.sum(r3)) / n
        if mu < kmu and rs < krs:
            info = 0
            break
        zdx = z / point
        QD = Q.copy()
        np.fill_diagonal(QD, np.diag(QD) + zdx)
        L = np.linalg.cholesky(QD)
        KT = np.linalg.solve(L, e)
        M = float(np.sum(KT * KT))
        r4 = r1 + r3 / point
        r5 = float(np.sum(KT * np.linalg.solve(L, r4)))
        dy = -(r2 + r5) / M
        dx = np.linalg.solve(L.T, np.linalg.solve(L, r4 + e * dy))
        dz = (r3 - z * dx) / point
        ap = _step_cap(point, dx)
        ad = _step_cap(z, dz)
        mauff = float(np.sum((point + ap * dx) * (z + ad * dz)) / n)
        sig = (mauff / mu) ** delta
        r3 = r3 + sig * mu - dx * dz
        r4 = r1 + r3 / point
        r5 = float(np.sum(KT * np.linalg.solve(L, r4)))
        dy = -(r2 + r5) / M
        dx = np.linalg.solve(L.T, np.linalg.solve(L, r4 + e * dy))
        dz = (r3 - z * dx) / point
        ap = _step_cap(point, dx)
        ad = _step_cap(z, dz)
        point = point + eta * ap * dx
        y = y + eta * ad * dy
        z = z + eta * ad * dz
    if k == maxit:
        info = 1
    point = np.maximum(point, 0)
    point = point / np.sum(point)
    d = matrix @ point
    q = float(np.sum(d * d))
    return {"x": point.reshape(-1, 1), "d": d.reshape(-1, 1), "q": q, "niter": k, "info": info}


def _step_cap(value, direction):
    ratio = -value / direction
    positive = ratio[ratio > 0]
    if positive.size:
        return float(min(np.min(positive), 1.0))
    return 1.0


def qpsolve(d, A, b, meq=0, tol=1e-07):
    sol = as_1d(d)
    bvec = as_1d(b)
    matrix = np.array(np.asarray(A, dtype=float), copy=True)
    imeq = list(range(int(meq)))
    Nmat = None
    wvec = np.array([])
    active = []
    niter = 0
    while True:
        niter += 1
        viol = matrix.T @ sol - bvec
        viol1 = viol / np.maximum(1, np.abs(bvec))
        if imeq:
            mask = viol1[imeq] >= tol
            if np.any(mask):
                iim = [imeq[i] for i, flag in enumerate(mask) if flag]
                viol[iim] *= -1
                bvec[iim] *= -1
                matrix[:, iim] *= -1
        ii = int(np.argmin(viol1))
        if viol1[ii] > -tol:
            break
        if ii in active:
            raise PracmaError("Error in projection")
        wvec = np.concatenate([wvec, [0.0]])
        active.append(ii)
        npvec = matrix[:, ii]
        if Nmat is not None:
            rvec, *_ = np.linalg.lstsq(Nmat, npvec, rcond=None)
            dvec = npvec - Nmat @ rvec
        else:
            dvec = npvec
            rvec = None
        if rvec is None:
            positive = np.array([], dtype=bool)
        else:
            positive = rvec > 0
            if positive.size:
                positive = positive.copy()
                positive[0] = False
        tmp = wvec[positive] / rvec[positive] if rvec is not None and np.any(positive) else np.array([])
        t1 = float(np.min(tmp)) if tmp.size else np.inf
        t2 = float(-viol[ii] / np.dot(npvec, dvec))
        t = min(t1, t2)
        if not np.isfinite(t) or t < 0 or t1 <= t2:
            raise PracmaError("Error in projection")
        sol = sol + t * dvec
        extra = np.array([-1.0]) if rvec is None else np.concatenate([rvec, [-1.0]])
        wvec = wvec - t * extra
        Nmat = npvec.reshape(-1, 1) if Nmat is None else np.column_stack([Nmat, npvec])
    value = 0.5 * float(np.sum(sol * sol)) - float(np.sum(as_1d(d) * sol))
    return {"sol": sol, "val": value, "niter": niter}
