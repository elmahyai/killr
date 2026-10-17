"""Likelihood ratio test under partly known beta in a subspace (``bh6lrtest``)."""

import warnings

import numpy as np

from urca.johansen import CaJo, CaJoTest, _as_matrix, _chol_pivot, _eigen_desc, _pchisq


def _deflate_s(s00, s0k, sk0, skk, beta):
    bkb = beta.T @ skk @ beta
    bkb_inv = np.linalg.solve(bkb, np.eye(bkb.shape[0]))
    proj = beta @ bkb_inv @ beta.T
    s00_b = s00 - s0k @ proj @ sk0
    s0k_b = s0k - s0k @ proj @ skk
    sk0_b = sk0 - skk @ proj @ sk0
    skk_b = skk - skk @ proj @ skk
    return s00_b, s0k_b, sk0_b, skk_b


def bh6lrtest(z, h, r, r1, conv_val=0.0001, max_iter=50):
    """Likelihood ratio test for restrictions under partly known beta in a subspace."""
    if not isinstance(z, CaJo):
        raise TypeError("Please, provide object of class 'ca.jo' as 'z'.")
    r = int(r)
    r1 = int(r1)
    if r >= z.P or r < 1:
        raise ValueError("Count of cointegrating relationships is out of allowable range.")
    p_h = z.P if z.ecdet == "none" else z.P + 1
    h_mat = _as_matrix(h)
    if h_mat.shape[0] != p_h:
        raise ValueError("Row number of 'H' is unequal to VAR order.")
    s_cols = h_mat.shape[1]
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
    d_chol = _chol_pivot(h_mat.T @ skk @ h_mat)
    dinv = np.linalg.solve(d_chol, np.eye(d_chol.shape[0]))
    s00inv = np.linalg.solve(s00, np.eye(s00.shape[0]))
    _, init_vecs = _eigen_desc(
        dinv @ h_mat.T @ sk0 @ s00inv @ s0k @ h_mat @ dinv.T
    )
    beta1 = h_mat @ init_vecs[:, :r1]
    iteration = 0
    last = 1.0
    lam_res = None
    beta2 = None
    while True:
        s00_b1, s0k_b1, sk0_b1, skk_b1 = _deflate_s(s00, s0k, sk0, skk, beta1)
        skk_vals, skk_vecs = _eigen_desc(skk_b1)
        k_c = p_h - r1
        scale = 1.0 / np.sqrt(skk_vals[:k_c])
        c_mat = skk_vecs[:, :k_c] * scale
        s00_b1_inv = np.linalg.solve(s00_b1, np.eye(s00_b1.shape[0]))
        lam_res, psi_raw = _eigen_desc(
            c_mat.T @ sk0_b1 @ s00_b1_inv @ s0k_b1 @ c_mat
        )
        diff = float(np.sum((lam_res - last) ** 2))
        last = lam_res
        beta2 = c_mat @ psi_raw[:, :r2]
        s00_b2, s0k_b2, sk0_b2, skk_b2 = _deflate_s(s00, s0k, sk0, skk, beta2)
        h_sh_vals, h_sh_vecs = _eigen_desc(h_mat.T @ skk_b2 @ h_mat)
        scale_h = 1.0 / np.sqrt(h_sh_vals[:s_cols])
        c_h = h_sh_vecs[:, :s_cols] * scale_h
        s00_b2_inv = np.linalg.solve(s00_b2, np.eye(s00_b2.shape[0]))
        _, beta1_vecs = _eigen_desc(
            c_h.T @ h_mat.T @ sk0_b2 @ s00_b2_inv @ s0k_b2 @ h_mat @ c_h
        )
        beta1 = h_mat @ beta1_vecs[:, :r1]
        iteration += 1
        if diff <= conv_val:
            break
        if iteration > max_iter:
            warnings.warn("\nNo convergence, used last iterations values.\n")
            break
    vorg = np.asmatrix(np.hstack([beta1, beta2]))
    idx = vorg.shape[1]
    v_norm = np.column_stack([vorg[:, j] / vorg[0, j] for j in range(idx)])
    vv = v_norm.T @ skk @ v_norm
    vv_inv = np.linalg.solve(vv, np.eye(vv.shape[0]))
    w = s0k @ v_norm @ vv_inv
    pi = w @ v_norm.T
    delta = s00 - s0k @ v_norm @ vv_inv @ v_norm.T @ sk0
    gamma = m01 @ m11inv - pi @ mk1 @ m11inv
    b1_chol = _chol_pivot(beta1.T @ skk @ beta1)
    b1_inv = np.linalg.solve(b1_chol, np.eye(b1_chol.shape[0]))
    rho_vals, _ = _eigen_desc(
        b1_inv @ beta1.T @ sk0 @ s00inv @ s0k @ beta1 @ b1_inv.T
    )
    base_lambda = np.asarray(z.lambda_, dtype=float)
    teststat = n * (
        np.sum(np.log(1.0 - rho_vals[:r1]))
        + np.sum(np.log(1.0 - lam_res[:r2]))
        - np.sum(np.log(1.0 - base_lambda[:r]))
    )
    df = (p_h - s_cols - r2) * r1
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
