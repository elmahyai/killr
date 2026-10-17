"""Level-shift Johansen procedure (``cajolst``) from urca 1.3-4."""

import warnings

import numpy as np

from urca.johansen import CaJo, _as_matrix, _chol_pivot, _eigen_desc, _embed, _names

_CV_TREND = np.array(
    [
        [5.42, 6.78, 10.04],
        [13.78, 15.83, 19.85],
        [25.93, 28.45, 33.76],
        [42.08, 45.20, 51.60],
        [61.92, 65.66, 73.12],
    ],
    dtype=float,
)

_CV_NOTREND = np.array(
    [
        [3.00, 4.12, 6.89],
        [10.45, 12.28, 16.42],
        [21.80, 24.28, 29.47],
        [36.90, 40.07, 46.30],
        [55.95, 59.75, 67.17],
    ],
    dtype=float,
)


def _lm_matrix(design, response):
    """R ``lm`` with matrix response (intercept included in design)."""
    coef, _resid, _rank, _sv = np.linalg.lstsq(design, response, rcond=None)
    residuals = response - design @ coef
    return coef, residuals


def cajolst(x, trend=True, K=2, season=None):
    """Johansen trace test after a level shift at an unknown time."""
    data = _as_matrix(x)
    colnames = _names(x, data.shape[1])
    K = int(K)
    if K < 2:
        raise ValueError("\nK must be at least K=2.\n")
    p_vars = data.shape[1]
    arrsel = p_vars
    n_obs = data.shape[0]
    season_count = 0 if season is None else int(season) - 1
    if n_obs * p_vars < p_vars + season_count * p_vars + K * p_vars ** 2 + p_vars * (p_vars + 1) / 2:
        raise ValueError("\nInsufficient degrees of freedom.\n")
    if p_vars > 5:
        warnings.warn("\nToo many variables, critical values cannot be computed.\n")
    dums = None
    if season is not None:
        season = int(season)
        dum = (np.eye(season) - 1 / season)[:, :-1]
        repeats = int(np.ceil(n_obs / season))
        dums = np.vstack([dum] * repeats)[:n_obs]
        if np.isnan(data).any():
            row_has_na = np.isnan(data).any(axis=1)
            keep = np.where(~row_has_na)[0]
            dums = dums[keep]
    x2 = data[~np.isnan(data).any(axis=1)] if np.isnan(data).any() else data
    n_tot = x2.shape[0]
    y = _embed(x2, K + 1)
    rhs = y[:, p_vars:]
    if trend:
        trd = np.arange(K + 1, y.shape[0] + K + 1, dtype=float)
        rhs = np.column_stack([trd, rhs])
    n_embed = y.shape[0]
    if season is not None:
        rhs = np.column_stack([dums[K:], rhs])
    lhs = y[:, :p_vars]
    idx = np.arange(1, n_embed)

    def tau(t):
        dt = np.concatenate([np.zeros(t), np.ones(n_embed - t)])
        design = np.column_stack([np.ones(n_embed), dt, rhs])
        _coef, resid = _lm_matrix(design, lhs)
        gram = resid.T @ resid
        return np.linalg.det(gram)

    tau_hat = np.array([tau(t) for t in idx])
    tau_opt = int(idx[np.argmin(tau_hat)]) + K
    tau_bp = tau_opt + 1
    dt = np.concatenate([np.zeros(tau_opt), np.ones(n_embed - tau_opt)])
    if not trend and season is None:
        rhs_aux = dt.reshape(-1, 1)
    else:
        drop_start = rhs.shape[1] - K * p_vars
        rhs_aux = np.column_stack([dt, rhs[:, :drop_start]])
    reg_coef, _ = _lm_matrix(np.column_stack([np.ones(n_embed), rhs_aux]), lhs)
    dt_full = np.concatenate([np.zeros(tau_opt), np.ones(n_tot - tau_opt)])
    uv = np.ones(n_tot)
    yfit = data.copy()
    if not trend:
        if season is not None:
            yfit = (
                data
                - np.outer(uv, reg_coef[0])
                - np.outer(dt_full, reg_coef[1])
                - dums @ reg_coef[2 : (2 + season - 1)]
            )
        else:
            yfit = data - np.outer(uv, reg_coef[0]) - np.outer(dt_full, reg_coef[1])
    else:
        trd_full = np.arange(1, n_tot + 1, dtype=float)
        if season is not None:
            yfit = (
                data
                - np.outer(uv, reg_coef[0])
                - np.outer(dt_full, reg_coef[1])
                - dums @ reg_coef[2 : (2 + season - 1)]
                - np.outer(trd_full, reg_coef[season + 1])
            )
        else:
            yfit = (
                data
                - np.outer(uv, reg_coef[0])
                - np.outer(dt_full, reg_coef[1])
                - np.outer(trd_full, reg_coef[2])
            )
    x_adj = yfit[~np.isnan(yfit).any(axis=1)]
    n_adj = x_adj.shape[0]
    z = _embed(np.diff(x_adj, axis=0), K)
    z0 = z[:, :p_vars]
    z1 = z[:, p_vars:]
    zk = x_adj[:-1][K - 1 : n_adj - 1]
    if trend:
        cvals = _CV_TREND
        model = "with linear trend in shift correction"
    else:
        cvals = _CV_NOTREND
        model = "without linear trend in shift correction"
    n_used = z0.shape[0]
    m00 = z0.T @ z0 / n_used
    m11 = z1.T @ z1 / n_used
    mkk = zk.T @ zk / n_used
    m01 = z0.T @ z1 / n_used
    m0k = z0.T @ zk / n_used
    mk0 = zk.T @ z0 / n_used
    m10 = z1.T @ z0 / n_used
    m1k = z1.T @ zk / n_used
    mk1 = zk.T @ z1 / n_used
    m11inv = np.linalg.solve(m11, np.eye(m11.shape[0]))
    r0 = z0 - (m01 @ m11inv @ z1.T).T
    rk = zk - (mk1 @ m11inv @ z1.T).T
    s00 = m00 - m01 @ m11inv @ m10
    s0k = m0k - m01 @ m11inv @ m1k
    sk0 = mk0 - mk1 @ m11inv @ m10
    skk = mkk - mk1 @ m11inv @ m1k
    chol_factor = _chol_pivot(skk)
    cinv = np.linalg.solve(chol_factor, np.eye(chol_factor.shape[0]))
    s00inv = np.linalg.solve(s00, np.eye(s00.shape[0]))
    lam, vectors = _eigen_desc(cinv @ sk0 @ s00inv @ s0k @ cinv.T)
    v_raw = cinv.T @ vectors
    vorg = v_raw.copy()
    v_norm = np.column_stack([v_raw[:, j] / v_raw[0, j] for j in range(v_raw.shape[1])])
    w = s0k @ v_norm @ np.linalg.solve(v_norm.T @ skk @ v_norm, np.eye(v_norm.shape[1]))
    pi = s0k @ np.linalg.solve(skk, np.eye(skk.shape[0]))
    delta = s00 - s0k @ v_norm @ np.linalg.solve(
        v_norm.T @ skk @ v_norm, np.eye(v_norm.shape[1])
    ) @ v_norm.T @ sk0
    gamma = m01 @ m11inv - pi @ mk1 @ m11inv
    type_name = "trace statistic"
    rank_idx = np.arange(p_vars)
    statistic = np.array(
        [n_used * np.sum(np.log(1.0 + lam[i:p_vars])) for i in rank_idx][::-1]
    )
    cval = None if arrsel > 5 else cvals[:arrsel].copy()
    z1_names = [f"{name}.dl{i}" for i in range(1, K) for name in colnames]
    zk_names = [f"{name}.l1" for name in colnames]
    return CaJo(
        x=x_adj,
        Z0=z0,
        Z1=z1,
        ZK=zk,
        type=type_name,
        model=model,
        ecdet="none",
        lag=K,
        P=arrsel,
        season=season,
        dumvar=None,
        cval=cval,
        teststat=statistic,
        lambda_=lam,
        Vorg=vorg,
        V=v_norm,
        W=w,
        PI=pi,
        DELTA=delta,
        GAMMA=gamma,
        R0=r0,
        RK=rk,
        bp=tau_bp,
        test_name="Johansen-Procedure",
        colnames=colnames,
        zk_names=zk_names,
        z1_names=z1_names,
    )
