"""Constrained Frisch-Newton solver, the Fortran lpfnc loop."""

from __future__ import annotations

import numpy as np
from scipy.linalg.lapack import dposv, dpotrs

from quantreg.interior import _as_observations


def _stepy2(a1, d1, a2, d2, rhs):
    p = a1.shape[0]
    gram = np.zeros((p, p), dtype=float, order="F")
    gram += (a1 * d1) @ a1.T
    if a2.shape[1]:
        gram += (a2 * d2) @ a2.T
    factor, solution, info = dposv(
        gram, np.array(rhs, dtype=float, order="F").reshape(-1, 1), lower=0, overwrite_a=1, overwrite_b=1
    )
    if info != 0:
        raise np.linalg.LinAlgError(str(info))
    return np.array(solution, dtype=float).reshape(-1), np.array(factor, dtype=float, order="F")


def _potrs(factor, rhs):
    solution, info = dpotrs(factor, np.array(rhs, dtype=float, order="F").reshape(-1, 1), lower=0, overwrite_b=1)
    if info != 0:
        raise np.linalg.LinAlgError(str(info))
    return np.array(solution, dtype=float).reshape(-1)


def _clip_step(value, direction, limit):
    neg = direction < 0
    if np.any(neg):
        return min(limit, np.min(-value[neg] / direction[neg]))
    return limit


def lpfnc(a1, c1, a2, c2, b, u, x1, x2, beta=0.9995, eps=1e-6):
    """Primal-dual loop with equality-style rows in a2."""
    n1 = c1.shape[0]
    n2 = c2.shape[0]
    y = a1 @ c1
    d1 = np.ones(n1)
    d2 = np.zeros(n2)
    z2 = np.ones(n2)
    nit = np.array([0, 0, n1], dtype=int)
    try:
        y, factor = _stepy2(a1, d1, a2, d2, y)
    except np.linalg.LinAlgError:
        return {"y": y, "nit": nit, "info": 1}
    s = c1 - a1.T @ y
    z1 = np.empty(n1)
    w = np.empty(n1)
    small = np.abs(s) < eps
    z1[small] = np.maximum(s[small], 0.0) + eps
    w[small] = np.maximum(-s[small], 0.0) + eps
    z1[~small] = np.maximum(s[~small], 0.0)
    w[~small] = np.maximum(-s[~small], 0.0)
    s = np.array(u, dtype=float)[:n1] - x1
    gap = float(z1 @ x1 + z2 @ x2 + w @ s)
    big = 1.0e20
    maxit = 500
    while gap > eps and nit[0] < maxit:
        nit[0] += 1
        r2 = c2 - a2.T @ y
        dy = b - a1 @ x1 - a2 @ x2
        d1 = 1.0 / (z1 / x1 + w / s)
        ds = z1 - w
        dz1 = d1 * ds
        d2 = x2 / z2
        dz2 = d2 * r2
        dy = dy + a1 @ dz1 + a2 @ dz2
        rhs = dy.copy()
        try:
            dy, factor = _stepy2(a1, d1, a2, d2, dy)
        except np.linalg.LinAlgError:
            return {"y": y, "nit": nit, "info": 1}
        ds = a1.T @ dy - ds
        dx1 = d1 * ds
        ds = -dx1
        dz1 = -z1 * (dx1 / x1 + 1.0)
        dw = -w * (ds / s + 1.0)
        deltap = big
        deltad = big
        deltap = _clip_step(x1, dx1, deltap)
        deltap = _clip_step(s, ds, deltap)
        deltad = _clip_step(z1, dz1, deltad)
        deltad = _clip_step(w, dw, deltad)
        dx2 = d2 * (a2.T @ dy - r2)
        dz2 = -z2 * (dx2 / x2 + 1.0)
        deltap = _clip_step(x2, dx2, deltap)
        deltad = _clip_step(z2, dz2, deltad)
        deltap = min(beta * deltap, 1.0)
        deltad = min(beta * deltad, 1.0)
        if min(deltap, deltad) < 1.0:
            nit[1] += 1
            mu = float(x1 @ z1 + x2 @ z2 + s @ w)
            g = (
                mu
                + deltap * float(dx1 @ z1)
                + deltad * float(dz1 @ x1)
                + deltap * deltad * float(dz1 @ dx1)
                + deltap * float(dx2 @ z2)
                + deltad * float(dz2 @ x2)
                + deltap * deltad * float(dz2 @ dx2)
                + deltap * float(ds @ w)
                + deltad * float(dw @ s)
                + deltap * deltad * float(ds @ dw)
            )
            mu = mu * ((g / mu) ** 3) / (2.0 * n1 + n2)
            dsdw = ds * dw
            dr1 = d1 * (mu * (1.0 / s - 1.0 / x1) + dx1 * dz1 / x1 - dsdw / s)
            dr2 = d2 * (dx2 * dz2 / x2 - mu / x2)
            dy, rhs = rhs, dy
            dy = dy + a1 @ dr1 + a2 @ dr2
            dy = _potrs(factor, dy)
            scratch = a1.T @ dy
            dxdz1 = dx1 * dz1
            dx1 = d1 * (scratch - z1 + w) - dr1
            ds = -dx1
            dz1 = -z1 + (mu - z1 * dx1 - dxdz1) / x1
            dw = -w + (mu - w * ds - dsdw) / s
            deltap = big
            deltad = big
            deltap = _clip_step(x1, dx1, deltap)
            deltap = _clip_step(s, ds, deltap)
            deltad = _clip_step(z1, dz1, deltad)
            deltad = _clip_step(w, dw, deltad)
            scratch2 = a2.T @ dy
            dxdz2 = dx2 * dz2
            dx2 = d2 * (scratch2 - r2) - dr2
            dz2 = -z2 + (mu - z2 * dx2 - dxdz2) / x2
            deltap = _clip_step(x2, dx2, deltap)
            deltad = _clip_step(z2, dz2, deltad)
            deltap = min(beta * deltap, 1.0)
            deltad = min(beta * deltad, 1.0)
        x1 = x1 + deltap * dx1
        x2 = x2 + deltap * dx2
        s = s + deltap * ds
        y = y + deltad * dy
        z1 = z1 + deltad * dz1
        z2 = z2 + deltad * dz2
        w = w + deltad * dw
        gap = float(z1 @ x1 + z2 @ x2 + w @ s)
    return {"y": y, "nit": nit, "info": 0}


def rq_fit_fnc(x, y, r_matrix, r, tau=0.5, beta=0.9995, eps=1e-6):
    """rq.fit.fnc. r_matrix is R in the R argument list."""
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    constraints = np.asarray(r_matrix, dtype=float)
    if constraints.ndim == 1:
        constraints = constraints.reshape(1, -1)
    bound = np.asarray(r, dtype=float).reshape(-1)
    n1, p = design.shape
    n2 = bound.shape[0]
    if response.shape[0] != n1:
        raise ValueError("x and y don't match n1")
    if constraints.shape[0] != n2:
        raise ValueError("R and r don't match n2")
    if constraints.shape[1] != p:
        raise ValueError("R and x don't match p")
    tau = float(tau)
    eps = float(eps)
    if tau < eps or tau > 1.0 - eps:
        raise ValueError("No parametric Frisch-Newton method.  Set tau in (0,1)")
    rhs = (1.0 - tau) * design.sum(axis=0)
    solved = lpfnc(
        _as_observations(design),
        -response,
        _as_observations(constraints),
        -bound,
        rhs,
        np.ones(max(n1, n2)),
        np.full(n1, 1.0 - tau),
        np.ones(n2),
        beta=float(beta),
        eps=eps,
    )
    if solved["info"] != 0:
        raise RuntimeError(f"Error info =  {solved['info']} in stepy2: singular design")
    coefficient = -solved["y"]
    return {
        "coefficients": coefficient,
        "tau": tau,
        "residuals": response - design @ coefficient,
        "it": solved["nit"],
    }
