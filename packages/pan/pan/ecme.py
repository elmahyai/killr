"""pan 2.0 ecme(): ML estimates for the linear mixed model by the ECME algorithm.

The loop is ecme3 in pan.f, with prelim, stval and nopsi, compiled and bound in
crates/pan_ecme. This wrapper does what ecme() does in R around the call: it numbers the
subjects in runs, checks the arguments, picks the nopsi or the ecme3 branch, forms the
covariance of beta as R does, and returns the random-effect covariances when asked.
Occasions are 1-based, as in R; xcol and zcol are 1-based columns of pred.
"""

import numpy as np
import pan_ecme

from pan._index import as_pred


def _subject_runs(subj):
    """Run number of each row, so that subjects in contiguous blocks get 1, 2, ...

    istfin needs contiguous subjects. Each run is one subject, as table(subj) counts it.
    """
    subj = np.asarray(subj).ravel()
    if subj.size == 0:
        return np.zeros(0, dtype=np.int32)
    change = np.r_[True, subj[1:] != subj[:-1]]
    return np.cumsum(change).astype(np.int32)


def ecme(y, subj, occ, pred, xcol, zcol=None, vmax=None, start=None, maxits=1000,
         eps=0.0001, random_effects=False):
    """ECME fit of the univariate linear mixed model (Schafer 1997).

    With zcol None, psi is zero and the GLS fit is returned, as in R's nopsi branch.
    Otherwise the ECME loop of ecme3 runs until beta, psi and sigma2 move by less than eps
    relatively, or maxits is reached. start, when given, holds beta, sigma2 and psi.
    vmax is the nmax x nmax working correlation; when None, V_i is the identity.
    Returns a dict with beta, sigma2, psi, converged, iter, loglik (None when zcol is
    None), cov_beta, bhat and cov_b (None unless random_effects is True).
    """
    y = np.asarray(y, dtype=float).ravel()
    codes = _subject_runs(subj)
    occ = np.asarray(occ, dtype=np.int32).ravel()
    pred = as_pred(pred)
    xcol = np.asarray(xcol, dtype=np.int32).ravel()
    vmat = None if vmax is None else np.asarray(vmax, dtype=float)

    if zcol is None:
        # R returns psi as a 1 x 1 zero matrix here, the loglikelihood as NULL, and the
        # unscaled inverse of X'WX (upper triangle) as cov.beta.
        out = pan_ecme.nopsi(codes, occ, pred, xcol, y, vmat)
        return {
            "beta": out["beta"],
            "sigma2": float(out["sigma2"]),
            "psi": np.zeros((1, 1)),
            "converged": True,
            "iter": 1,
            "loglik": None,
            "cov_beta": np.triu(out["xtwxinv"]),
            "bhat": None,
            "cov_b": None,
        }

    zcol = np.asarray(zcol, dtype=np.int32).ravel()
    start_kw = {}
    if start is not None:
        start_kw = dict(
            beta=np.asarray(start["beta"], dtype=float).ravel(),
            sigma2=float(start["sigma2"]),
            psi=np.asarray(start["psi"], dtype=float),
        )
    out = pan_ecme.ecme3(codes, occ, pred, xcol, zcol, y, vmat, eps=float(eps),
                         maxits=int(maxits), **start_kw)

    # R: cov.beta <- xtwxinv * sigma2; cov.beta + t(cov.beta) - diag(cov.beta). The vector
    # diag() is recycled down the columns, so row i loses diag[i] from every entry.
    a = out["xtwxinv"] * out["sigma2"]
    cov_beta = a + a.T - np.diag(a)[:, None]
    bhat = None
    cov_b = None
    if random_effects:
        bhat = out["b"]
        cov_b = pan_ecme.bdiag(out["sig"])
    return {
        "beta": out["beta"],
        "sigma2": float(out["sigma2"]),
        "psi": out["psi"],
        "converged": bool(out["converged"]),
        "iter": int(out["iter"]),
        "loglik": out["llk"],
        "cov_beta": cov_beta,
        "bhat": bhat,
        "cov_b": cov_b,
    }
