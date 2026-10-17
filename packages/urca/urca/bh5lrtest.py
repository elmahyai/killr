"""Likelihood ratio test under partly known beta (``bh5lrtest``)."""

import numpy as np

from urca.johansen import CaJo, CaJoTest, _as_matrix, _chol_pivot, _eigen_desc, _pchisq


def bh5lrtest(z, h, r):
    """Likelihood ratio test when some cointegration vectors are known."""
    if not isinstance(z, CaJo):
        raise TypeError("Please, provide object of class 'ca.jo' as 'z'.")
    r = int(r)
    if r >= z.P or r < 1:
        raise ValueError("Count of cointegrating relationships is out of allowable range.")
    p_h = z.P if z.ecdet == "none" else z.P + 1
    h_mat = _as_matrix(h)
    if h_mat.shape[0] != p_h:
        raise ValueError("Row number of 'H' is unequal to VAR order.")
    if h_mat.shape[1] > r - 1:
        raise ValueError("Too many columns in H for provided r.")
    r1 = h_mat.shape[1]
    r2 = r - r1
    n = z.Z0.shape[0]
    z0 = np.asarray(z.Z0, dtype=float)
    z1 = np.asarray(z.Z1, dtype=float)
    zk = np.asarray(z.ZK, dtype=float)
    m00 = z0.T @ z0 / n
    m11 = z1.T @ z1 / n
    mkk = zk.T @ zk / n
    m01 = z0.T @ z1 / n
    m0k = z0.T @ zk / n
    mk0 = zk.T @ z0 / n
    m10 = z1.T @ z0 / n
    m1k = z1.T @ zk / n
    mk1 = zk.T @ z1 / n
    m11inv = np.linalg.solve(m11, np.eye(m11.shape[0]))
    s00 = m00 - m01 @ m11inv @ m10
    s0k = m0k - m01 @ m11inv @ m1k
    sk0 = mk0 - mk1 @ m11inv @ m10
    skk = mkk - mk1 @ m11inv @ m1k
    h_sh = h_mat.T @ skk @ h_mat
    h_sh_inv = np.linalg.solve(h_sh, np.eye(h_sh.shape[0]))
    s00_h = s00 - s0k @ h_mat @ h_sh_inv @ h_mat.T @ sk0
    s0k_h = s0k - s0k @ h_mat @ h_sh_inv @ h_mat.T @ skk
    sk0_h = sk0 - skk @ h_mat @ h_sh_inv @ h_mat.T @ sk0
    skk_h = skk - skk @ h_mat @ h_sh_inv @ h_mat.T @ skk
    skk_vals, skk_vecs = _eigen_desc(skk_h)
    k_c = p_h - r1
    scale = 1.0 / np.sqrt(skk_vals[:k_c])
    c_mat = skk_vecs[:, :k_c] * scale
    s00_h_inv = np.linalg.solve(s00_h, np.eye(s00_h.shape[0]))
    middle = c_mat.T @ sk0_h @ s00_h_inv @ s0k_h @ c_mat
    lam_res, psi_raw = _eigen_desc(middle)
    psi = c_mat @ psi_raw[:, :r2]
    c_chol = _chol_pivot(h_mat.T @ skk @ h_mat)
    cinv = np.linalg.solve(c_chol, np.eye(c_chol.shape[0]))
    s00inv = np.linalg.solve(s00, np.eye(s00.shape[0]))
    rho_vals, _ = _eigen_desc(
        cinv @ h_mat.T @ sk0 @ s00inv @ s0k @ h_mat @ cinv.T
    )
    vorg = np.asmatrix(np.hstack([h_mat, psi]))
    idx = psi.shape[1]
    psi_norm = np.column_stack([psi[:, j] / psi[0, j] for j in range(idx)])
    v_norm = np.hstack([h_mat, psi_norm])
    vv = v_norm.T @ skk @ v_norm
    vv_inv = np.linalg.solve(vv, np.eye(vv.shape[0]))
    w = s0k @ v_norm @ vv_inv
    pi = w @ v_norm.T
    delta = s00 - s0k @ v_norm @ vv_inv @ v_norm.T @ sk0
    gamma = m01 @ m11inv - pi @ mk1 @ m11inv
    base_lambda = np.asarray(z.lambda_, dtype=float)
    teststat = n * (
        np.sum(np.log(1.0 - rho_vals[:r1]))
        + np.sum(np.log(1.0 - lam_res[:r2]))
        - np.sum(np.log(1.0 - base_lambda[:r]))
    )
    df = (p_h - r) * r1
    pval = np.array([1.0 - _pchisq(teststat, df, lower_tail=True), float(df)])
    return CaJoTest(
        Z0=z0,
        Z1=z1,
        ZK=zk,
        ecdet=z.ecdet,
        H=h_mat,
        A=None,
        B=None,
        type="Estimation and testing under partly known beta",
        teststat=float(teststat),
        pval=pval,
        lambda_=lam_res,
        Vorg=vorg,
        V=v_norm,
        W=w,
        PI=pi,
        DELTA=delta,
        DELTA_bb=None,
        DELTA_ab=None,
        DELTA_aa_b=None,
        GAMMA=gamma,
        test_name="Johansen-Procedure",
    )
