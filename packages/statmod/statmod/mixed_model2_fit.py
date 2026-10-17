"""REML mixed linear model core fit (two variance components).

Translated from statmod 1.5.2 ``mixedModel2Fit`` / ``randomizedBlockFit`` in
``R/mixedmodel.R``.
"""

from __future__ import annotations

import numpy as np

from statmod.glmgam_fit import glmgam_fit
from statmod.vecmat import vecmat


def _lm_rank(x: np.ndarray) -> int:
    _, r = np.linalg.qr(x, mode="reduced")
    if r.size == 0:
        return 0
    tol = np.finfo(float).eps * max(x.shape) * abs(r[0, 0])
    return int(np.sum(np.abs(np.diag(r)) > tol))


def _lm_fit_effects(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, int]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    q, _r = np.linalg.qr(x, mode="complete")
    effects = q.T @ y
    rank = _lm_rank(x)
    return effects, rank


def _la_svd(x: np.ndarray, *, nu: int, nv: int = 0) -> dict[str, np.ndarray]:
    x = np.asarray(x, dtype=float)
    u_full, s, _vh = np.linalg.svd(x, full_matrices=True)
    return {"u": u_full[:, :nu], "d": s}


def _chol2inv_qr(qr_mat: np.ndarray, rank: int) -> np.ndarray:
    r = np.asarray(qr_mat, dtype=float)[:rank, :rank]
    inv_r = np.linalg.inv(r)
    return inv_r @ inv_r.T


def _lm_fit(x: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    q, r = np.linalg.qr(x, mode="reduced")
    coef = np.linalg.solve(r, q.T @ y)
    return {"coefficients": coef, "fitted.values": x @ coef}


def _lm_wfit(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> dict[str, np.ndarray]:
    sw = np.sqrt(np.asarray(w, dtype=float).reshape(-1))
    xw = x * sw[:, None]
    yw = y * sw
    q, r = np.linalg.qr(xw, mode="reduced")
    rank = _lm_rank(xw)
    coef = np.linalg.solve(r, q.T @ yw)
    qr_mat = np.zeros_like(xw)
    qr_mat[: r.shape[0], : r.shape[1]] = r
    return {"coefficients": coef, "rank": rank, "qr": {"qr": qr_mat}}


def mixed_model2_fit(
    y,
    x,
    z,
    w=None,
    only_varcomp=False,
    tol=1e-6,
    maxit=50,
    trace=False,
):
    """Fit mixed model ``y = X beta + Z u + e`` by REML (two variance components)."""
    y = np.asarray(y, dtype=float).reshape(-1)
    x = np.asarray(x, dtype=float)
    z = np.asarray(z, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if z.ndim == 1:
        z = z.reshape(-1, 1)

    if w is not None:
        sw = np.sqrt(np.asarray(w, dtype=float).reshape(-1))
        y = sw * y
        x = sw[:, None] * x

    mx = x.shape[0]
    joint = np.column_stack([z, y])
    effects, rank = _lm_fit_effects(x, joint)
    nz = z.shape[1]
    mq = mx - rank
    if mq == 0:
        return {"varcomp": np.array([np.nan, np.nan], dtype=float)}

    qtz = effects[rank:mx, :nz]
    s = _la_svd(qtz, nu=mq, nv=0)
    uqy = s["u"].T @ effects[rank:mx, nz]
    d = np.zeros(mq, dtype=float)
    d[: s["d"].size] = s["d"] ** 2
    dx = np.column_stack([np.ones(mq), d])
    dy = uqy**2

    dfit = _lm_fit(dx, dy)
    dfitted = dfit["fitted.values"]

    if mq > 2 and np.sum(np.abs(d) > 1e-15) > 1 and np.var(d) > 1e-15:
        if np.all(dfitted >= 0):
            start = dfit["coefficients"]
        else:
            start = np.array([float(np.mean(dy)), 0.0], dtype=float)
        dfit = glmgam_fit(dx, dy, coef_start=start, tol=tol, maxit=maxit, trace=trace)
        dfitted = dfit["fitted.values"]

    out: dict[str, np.ndarray] = {
        "varcomp": np.asarray(dfit["coefficients"], dtype=float).reshape(-1)
    }
    if only_varcomp:
        return out

    varcomp = out["varcomp"]
    dinfo = dx.T @ vecmat(1.0 / dfitted**2, dx)
    out["se.varcomp"] = np.sqrt(2.0 * np.diag(np.linalg.inv(dinfo)))

    s2 = _la_svd(z, nu=mx, nv=0)
    d2 = np.zeros(mx, dtype=float)
    d2[: s2["d"].size] = s2["d"] ** 2
    v = (np.column_stack([np.ones(mx), d2]) @ varcomp).reshape(-1)
    xrot = s2["u"].T @ x
    yrot = s2["u"].T @ y
    mfit = _lm_wfit(xrot, yrot, 1.0 / v)
    out["coefficients"] = mfit["coefficients"]
    inv_coef = _chol2inv_qr(mfit["qr"]["qr"], mfit["rank"])
    out["se.coefficients"] = np.sqrt(np.diag(inv_coef))
    return out


randomized_block_fit = mixed_model2_fit
