"""Granger and instantaneous causality for an unrestricted VAR."""

import numpy as np
from scipy.linalg import qr
from scipy.stats import chi2, f as f_dist

from .estimate import residuals


def _duplicate(n):
    out = np.zeros((n * n, n * (n + 1) // 2))
    count = 0
    for j in range(1, n + 1):
        out[(j - 1) * n + j - 1, count + j - 1] = 1
        if j + 1 <= n:
            for i in range(j + 1, n + 1):
                out[(j - 1) * n + i - 1, count + i - 1] = 1
                out[(i - 1) * n + j - 1, count + i - 1] = 1
        count += n - j
    return out


def _ginv(matrix):
    """Moore-Penrose inverse, the same cutoff MASS::ginv uses."""
    u, d, vt = np.linalg.svd(matrix, full_matrices=False)
    tol = np.sqrt(np.finfo(float).eps)
    keep = d > max(tol * d[0] if d.size else 0.0, 0.0)
    if not np.any(keep):
        return np.zeros((matrix.shape[1], matrix.shape[0]))
    return (vt.T[:, keep] * (1.0 / d[keep])) @ u[:, keep].T


def causality(x, cause=None):
    names = list(x.names)
    if cause is None:
        cause = [names[0]]
    cause = [cause] if isinstance(cause, str) else list(cause)
    k = x.K
    lag_names = [name for name in x.datamat_names[k:] if name != "const"]
    coef = x.coefficients
    const = "const" in x.datamat_names
    rows = (["(Intercept)"] if const else []) + lag_names
    pi = np.column_stack([
        np.concatenate([[coef[i, -1]], coef[i, :-1]]) if const else coef[i]
        for i in range(k)
    ])
    pi_vec = pi.reshape(-1, order="F")
    design_names = rows
    response = names
    mask = np.zeros_like(pi)
    # gsub("\\.l\\d+", "") strips one ".l" and its digits, so "e.l1" becomes "e".
    cause_rows = []
    for i, name in enumerate(design_names):
        stem = name
        while True:
            cut = stem.rfind(".l")
            if cut < 0:
                break
            tail = stem[cut + 2:]
            if tail.isdigit():
                stem = stem[:cut]
                break
            break
        if stem in cause:
            cause_rows.append(i)
    cause_cols = [i for i, name in enumerate(response) if name in cause]
    other_cols = [i for i in range(k) if i not in cause_cols]
    for row in cause_rows:
        for col in other_cols:
            mask[row, col] = 1
    which = np.flatnonzero(mask.reshape(-1, order="F"))
    n_rest = which.size
    restriction = np.zeros((n_rest, pi_vec.size))
    for i, position in enumerate(which):
        restriction[i, position] = 1
    resid = residuals(x)
    df = x.varresult[names[0]]["df_residual"]
    est_var = resid.T @ resid / df
    z = np.column_stack([np.ones(x.obs), x.datamat[:, k:k + len(lag_names)]]) if const else x.datamat[:, k:k + len(lag_names)]
    # R's cov.unscaled is chol2inv of the pivoted QR, then scattered back to the original columns.
    _q, rr, piv = qr(z, mode="economic", pivoting=True)
    rank = int(np.sum(np.abs(np.diag(rr)) > np.max(np.abs(rr)) * np.sqrt(np.finfo(float).eps)))
    inv = np.linalg.inv(rr[:rank, :rank])
    unscaled = np.zeros((z.shape[1], z.shape[1]))
    unscaled[np.ix_(piv[:rank], piv[:rank])] = inv @ inv.T
    sigma_pi = np.kron(est_var, unscaled)
    middle = restriction @ sigma_pi @ restriction.T
    contrast = restriction @ pi_vec
    statistic = float(contrast @ np.linalg.solve(middle, contrast) / n_rest)
    df1 = x.p * len(cause) * len(other_cols)
    df2 = k * x.obs - pi.size
    pvalue = float(f_dist.sf(statistic, df1, df2))
    sigma_u = resid.T @ resid / (x.obs - z.shape[1])
    y1 = [i for i, name in enumerate(names) if name in cause]
    y2 = [i for i, name in enumerate(names) if name not in cause]
    select = sigma_u[np.ix_(y2, y1)].reshape(-1, order="F")
    # R lower.tri walks down each column, so the diagonal of column j comes before the entries below it.
    vech = np.array([sigma_u[i, j] for j in range(k) for i in range(j, k)])
    index = [i for i, value in enumerate(vech) if np.any(value == select)]
    cmat = np.zeros((len(index), vech.size))
    for i, position in enumerate(index):
        cmat[i, position] = 1
    dinv = _ginv(_duplicate(k))
    bread = cmat @ dinv @ np.kron(sigma_u, sigma_u) @ dinv.T @ cmat.T
    instant = float(x.obs * vech @ cmat.T @ np.linalg.solve(2 * bread, cmat @ vech))
    return {
        "Granger": {"statistic": statistic, "df": (df1, df2), "p_value": pvalue},
        "Instant": {"statistic": instant, "df": len(index), "p_value": float(chi2.sf(instant, len(index)))},
    }
