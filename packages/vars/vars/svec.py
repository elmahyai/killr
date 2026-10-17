"""Structural VECM. The bootstrap standard errors use R's RNG and are not computed."""

import numpy as np
from scipy.linalg import qr
from scipy.stats import chi2

from urca.johansen import CaJo, cajorls


def null_space(matrix):
    """Orthonormal basis returned by MASS::Null.

    R's qr moves a column to the right when its norm falls below 1e-7 times
    its original norm, and otherwise keeps the column order. That is the
    basis MASS::Null returns.
    """
    matrix = np.atleast_2d(np.asarray(matrix, dtype=float))
    if matrix.shape[0] == 0 or matrix.shape[1] == 0:
        return np.zeros((matrix.shape[0], 0))
    ordered, kept = _r_column_order(matrix)
    q, r = qr(ordered, mode="full", pivoting=False)
    diag = np.abs(np.diag(r[:kept, :kept])) if kept else np.array([])
    tol = max(matrix.shape) * np.finfo(float).eps * (diag[0] if diag.size else 0.0)
    rank = int(np.sum(diag > tol)) if kept else 0
    return q[:, rank:]


def _r_column_order(matrix, tol=1e-7):
    """Move columns whose norm is below tol times the original norm to the end."""
    columns = [matrix[:, j].copy() for j in range(matrix.shape[1])]
    original = [np.linalg.norm(column) for column in columns]
    kept = []
    dropped = []
    for column, norm0 in zip(columns, original):
        if norm0 == 0.0:
            dropped.append(column)
        else:
            kept.append(column)
    ordered = kept + dropped
    if not ordered:
        return matrix.copy(), 0
    return np.column_stack(ordered), len(kept)


def SVEC(x, LR, SR, r=1, start=None, max_iter=100, conv_crit=1e-7, maxls=1.0, lrtest=True, boot=False):
    if not isinstance(x, CaJo):
        raise TypeError("provide an object from ca_jo")
    if boot:
        raise ValueError("bootstrap standard errors use R's RNG; call SVEC with boot=False")
    LR = np.array(LR, dtype=float, copy=True)
    SR = np.array(SR, dtype=float, copy=True)
    k = int(x.P)
    if LR.shape != (k, k) or SR.shape != (k, k):
        raise ValueError(f"LR and SR must be {k} by {k}")
    r = int(r)
    vecr = cajorls(x, r=r)
    resid = vecr["rlm"]["residuals"]
    obs = resid.shape[0]
    sigma = resid.T @ resid / obs
    coef = vecr["rlm"]["coef"]
    # R transposes the coefficient block, then transposes again when r is 1
    # because a single row drops to a vector and t() turns that vector into a row.
    alpha = coef[:r].T
    alpha_orth = null_space(alpha)
    beta = np.asarray(vecr["beta"][:k], dtype=float)
    if beta.ndim == 1:
        beta = beta.reshape(-1, 1)
    beta_orth = null_space(beta)
    lag_rows = coef[r:]
    # tail(coef, K*P) with P = lag - 1. The lag block is the trailing K*(lag-1) rows.
    p_lag = int(x.lag) - 1
    gamma_flat = lag_rows[-k * p_lag:].T if p_lag else np.zeros((k, 0))
    gamma = np.zeros((k, k))
    for block in range(p_lag):
        gamma = gamma + gamma_flat[:, block * k:(block + 1) * k]
    eye = np.eye(k)
    xi = beta_orth @ np.linalg.solve(alpha_orth.T @ (eye - gamma) @ beta_orth, np.eye(beta_orth.shape[1])) @ alpha_orth.T
    eye_sq = np.eye(k * k)
    r_b = _zero_rows(SR, eye_sq)
    r_c = _zero_rows(LR, eye_sq)
    if r_c.shape[0] == 0:
        r_c = np.zeros((k * k, k * k))
        n_res_c = 0
    else:
        r_c = r_c @ np.kron(eye, xi)
        n_res_c = _qr_rank(r_c)
    if r_b.shape[0] == 0:
        restriction = r_c
        n_res_b = 0
    else:
        restriction = np.vstack([r_c, r_b])
        n_res_b = _qr_rank(r_b)
    if n_res_b + n_res_c < k * (k - 1) / 2:
        raise ValueError("the model is not identified")
    sb = null_space(restriction.T)
    selector = np.vstack([np.zeros((k * k, sb.shape[1])), sb])
    fixed = np.concatenate([np.eye(k).reshape(-1, order="F"), np.zeros(k * k)])
    length = selector.shape[1]
    if start is None:
        raise ValueError("pass start; the R default draws it with rnorm")
    gamma_par = np.asarray(start, dtype=float).reshape(-1)
    if gamma_par.size != length:
        raise ValueError(f"start must have length {length}")
    k2 = k * k
    order = [index for i in range(k) for index in range(i, k2, k)]
    commutation = np.eye(k2)[:, order]
    iteration = 0
    criterion = conv_crit + 1
    current_a = current_b = None
    while criterion > conv_crit:
        previous = gamma_par.copy()
        vec = selector @ gamma_par + fixed
        current_a = vec[:k2].reshape((k, k), order="F")
        current_b = vec[k2:].reshape((k, k), order="F")
        binv = np.linalg.inv(current_b)
        btinv = np.linalg.inv(current_b.T)
        binv_a = binv @ current_a
        mat1 = np.vstack([np.kron(np.linalg.inv(binv_a), btinv), -np.kron(eye, btinv)])
        mat3 = np.hstack([np.kron(np.linalg.inv(binv_a).T, binv), -np.kron(eye, binv)])
        info_ab = obs * (mat1 @ (eye_sq + commutation) @ mat3)
        info = selector.T @ info_ab @ selector
        info_inv = np.linalg.inv(info)
        score_inner = obs * np.linalg.inv(binv_a).T.reshape(-1, order="F") - obs * (np.kron(sigma, eye) @ binv_a.reshape(-1, order="F"))
        score_mat = np.vstack([np.kron(eye, btinv), -np.kron(binv_a, btinv)])
        direction = info_inv @ (selector.T @ (score_mat @ score_inner))
        step_length = np.max(np.abs(direction))
        step = 1.0 if step_length <= maxls else maxls / step_length
        gamma_par = gamma_par + step * direction
        iteration += 1
        criterion = np.max(np.abs(previous - gamma_par))
        if iteration >= max_iter:
            break
    impact = np.linalg.solve(current_a, current_b)
    for index in np.flatnonzero(np.diag(impact) < 0):
        current_b[:, index] *= -1
    long_run = xi @ current_b
    sigma_u = impact @ impact.T
    long_run[np.abs(long_run) < 1e-9] = 0.0
    current_b[np.abs(current_b) < 1e-9] = 0.0
    over = None
    degrees = k * (k + 1) / 2 - length
    if lrtest and degrees != 0:
        statistic = (np.log(np.linalg.det(sigma_u)) - np.log(np.linalg.det(sigma))) * obs
        over = {"statistic": float(statistic), "parameter": degrees, "p_value": float(chi2.sf(statistic, degrees))}
    return {
        "SR": current_b,
        "LR": long_run,
        "Sigma_U": sigma_u * 100,
        "iter": iteration - 1,
        "LRover": over,
        "r": r,
    }


def _zero_rows(matrix, eye_sq):
    flat = matrix.reshape(-1, order="F")
    keep = np.array([value == 0.0 and not np.isnan(value) for value in flat])
    return eye_sq[keep]


def _qr_rank(matrix):
    _q, r, _piv = qr(matrix, mode="economic", pivoting=True)
    if r.size == 0:
        return 0
    diag = np.abs(np.diag(r))
    tol = max(matrix.shape) * np.finfo(float).eps * diag[0]
    return int(np.sum(diag > tol))
