"""Likelihood ratio test for linear restrictions on beta (``blrtest``)."""

import numpy as np

from urca.johansen import CaJo, CaJoTest, _as_matrix, _chol_pivot, _eigen_desc, _pchisq


def blrtest(z, h, r):
    """Likelihood ratio test for linear restrictions on the cointegration matrix beta."""
    if not isinstance(z, CaJo):
        raise TypeError("Please, provide object of class 'ca.jo' as 'z'.")
    r = int(r)
    if r >= z.P or r < 1:
        raise ValueError("Count of cointegrating relationships is out of allowable range.")
    p_h = z.P if z.ecdet == "none" else z.P + 1
    h_mat = _as_matrix(h)
    if h_mat.shape[0] != p_h:
        raise ValueError("Row number of 'H' is unequal to VAR order.")
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
    c = _chol_pivot(h_mat.T @ skk @ h_mat)
    cinv = np.linalg.solve(c, np.eye(c.shape[0]))
    s00inv = np.linalg.solve(s00, np.eye(s00.shape[0]))
    lam_res, vectors = _eigen_desc(
        cinv @ h_mat.T @ sk0 @ s00inv @ s0k @ h_mat @ cinv.T
    )
    v_raw = h_mat @ cinv.T @ vectors
    vorg = np.asmatrix(v_raw)
    idx = v_raw.shape[1]
    v_norm = np.column_stack([v_raw[:, j] / v_raw[0, j] for j in range(idx)])
    vv = v_norm.T @ skk @ v_norm
    vv_inv = np.linalg.solve(vv, np.eye(vv.shape[0]))
    w = s0k @ v_norm @ vv_inv
    pi = w @ v_norm.T
    delta = s00 - s0k @ v_norm @ vv_inv @ v_norm.T @ sk0
    gamma = m01 @ m11inv - pi @ mk1 @ m11inv
    base_lambda = np.asarray(z.lambda_, dtype=float)
    teststat = n * np.sum(np.log((1.0 - lam_res[:r]) / (1.0 - base_lambda[:r])))
    df = r * (p_h - h_mat.shape[1])
    pval = np.array([1.0 - _pchisq(teststat, df, lower_tail=True), float(df)])
    return CaJoTest(
        Z0=z0,
        Z1=z1,
        ZK=zk,
        ecdet=z.ecdet,
        H=h_mat,
        A=None,
        B=None,
        type="Estimation and testing under linear restrictions on beta",
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
