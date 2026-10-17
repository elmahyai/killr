"""Covariance estimation for multivariate t (MASS cov.trob)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

from mass.errors import MassError


def _test_values(x: np.ndarray) -> None:
    if np.any(~np.isfinite(x)):
        raise MassError("missing or infinite values in 'x'")


def _scale_simp(x: np.ndarray, center: np.ndarray) -> np.ndarray:
    return x - center


@dataclass
class CovTrob:
    cov: np.ndarray
    center: np.ndarray
    n_obs: int
    iter: int
    wt: np.ndarray | None = None
    cor: np.ndarray | None = None
    call: Any = None


def cov_trob(
    x,
    wt: np.ndarray | None = None,
    cor: bool = False,
    center: bool | np.ndarray = True,
    nu: float = 5,
    maxit: int = 25,
    tol: float = 0.01,
) -> CovTrob:
    """Estimate covariance assuming a multivariate t distribution."""
    matrix = np.asarray(x, dtype=float)
    if matrix.ndim != 2:
        matrix = np.atleast_2d(matrix)
    n, p = matrix.shape
    _test_values(matrix)

    miss_wt = wt is None
    wt0: np.ndarray | None = None
    if not miss_wt:
        wt0 = np.asarray(wt, dtype=float).reshape(-1)
        _test_values(wt0)
        if wt0.size != n:
            raise MassError("length of 'wt' must equal number of observations")
        if np.any(wt0 < 0):
            raise MassError("negative weights not allowed")
        if not np.sum(wt0):
            raise MassError("no positive weights")
        keep = wt0 > 0
        matrix = matrix[keep, :]
        wt_work = wt0[keep]
        n = matrix.shape[0]
    else:
        wt_work = np.ones(n, dtype=float)

    loc = np.sum(wt_work[:, None] * matrix, axis=0) / np.sum(wt_work)
    if isinstance(center, (np.ndarray, list, tuple)):
        center_arr = np.asarray(center, dtype=float).reshape(-1)
        if center_arr.size != p:
            raise MassError("'center' is not the right length")
        loc = center_arr
        use_loc = False
    elif center is False:
        loc = np.zeros(p, dtype=float)
        use_loc = False
    else:
        use_loc = True

    w = wt_work * (1.0 + p / nu)
    endit = 0
    x_scaled: np.ndarray | None = None
    q: np.ndarray | None = None
    for iter_idx in range(1, maxit + 1):
        w0 = w.copy()
        x_scaled = _scale_simp(matrix, loc)
        scale = np.sqrt(w / np.sum(w))
        scaled = scale[:, None] * x_scaled
        _, sX_d, sX_vt = np.linalg.svd(scaled, full_matrices=True)
        sX_v = sX_vt.T
        inv_d = np.diag(1.0 / sX_d)
        w_x = x_scaled @ sX_v @ inv_d
        q = np.sum(w_x * w_x, axis=1)
        w = (wt_work * (nu + p)) / (nu + q)
        if use_loc:
            loc = np.sum(w[:, None] * matrix, axis=0) / np.sum(w)
        if np.all(np.abs(w - w0) < tol):
            break
        endit = iter_idx

    if x_scaled is None or q is None:
        raise MassError("no iterations completed")

    if endit == maxit or abs(float(np.mean(w)) - float(np.mean(wt_work))) > tol or abs(
        float(np.mean(w * q)) / p - 1.0
    ) > tol:
        warnings.warn("Probable convergence failure", stacklevel=2)

    sqrt_w_x = np.sqrt(w)[:, None] * x_scaled
    cov = sqrt_w_x.T @ sqrt_w_x / np.sum(wt_work)

    ans = CovTrob(cov=cov, center=loc, n_obs=n, iter=endit)
    if not miss_wt:
        ans.wt = wt0
    if cor:
        sd = np.sqrt(np.diag(cov))
        ans.cor = (cov / sd[:, None]) / sd[None, :]
    return ans
