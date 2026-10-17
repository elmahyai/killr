"""pan 2.0 mgibbsbd(): the R-side work before the Fortran routine mgibbsbd, then the kernel.

In R, pan.bd() checks pred, builds the missing-data indexes (patt, rmat, iposn, pstfin),
packs a, Binv, c (length r) and Dinv (q x q x r) into hyp, seeds the generator with rngs,
calls .Fortran("mgibbsbd", ...), and shapes the output list. psi is block diagonal: one
q x q block per response column. This module calls the Rust port of mgibbsbd in pan.f
(crates/pan_mgibbs).
"""

import numpy as np
import pan_mgibbs

from pan._index import as_pred, as_response, hyp_bd, kernel_y, missing_patterns
from pan.mgibbs import _check_contiguous


def mgibbsbd(y, subj, pred, xcol, zcol, prior, seed, iter=1, start=None):
    """Gibbs sampler for the multivariate linear mixed model with block-diagonal psi.

    xcol and zcol are 1-based column numbers of pred, as in R. prior holds a, Binv, c
    (length r) and Dinv (q x q x r). start, when given, holds beta, sigma, psi (q x q x r)
    and y (the starting eps). Returns a dict with beta (p x r x iter), sigma (r x r x iter),
    psi (q x q x r x iter), y (the imputed response) and last (the final state: beta, sigma,
    psi, y).
    """
    y = as_response(y)
    pred = as_pred(pred)
    if np.isnan(pred).any():
        raise ValueError("missing values in pred not allowed")
    subj = np.asarray(subj, dtype=np.int64).ravel()
    _check_contiguous(subj)
    xcol = np.asarray(xcol, dtype=np.int64).ravel()
    zcol = np.asarray(zcol, dtype=np.int64).ravel()
    ntot, r = y.shape
    q = zcol.size

    patt, rmat, iposn, pstfin, _ = missing_patterns(y)
    hyp = hyp_bd(prior, r, q)

    if start is None:
        sflag, beta, sigma, psi, eps = 0, None, None, None, None
    else:
        sflag = 1
        beta = np.asarray(start["beta"], dtype=float)
        sigma = np.asarray(start["sigma"], dtype=float)
        psi = np.asarray(start["psi"], dtype=float)
        eps = as_response(start["y"])

    pan_mgibbs.rngs(int(seed))  # rngs before the sampler, as pan.bd() does
    chain = pan_mgibbs.mgibbsbd(
        subj, pred, zcol, xcol, patt, rmat, iposn, pstfin,
        kernel_y(y), hyp, int(iter), sflag, beta, sigma, psi, eps,
    )
    y_out = chain["y"][:, 0] if r == 1 else chain["y"]  # R returns a vector when r == 1
    return {
        "beta": chain["betas"],
        "sigma": chain["sigmas"],
        "psi": chain["psis"],
        "y": y_out,
        "last": {"beta": chain["beta"], "sigma": chain["sigma"], "psi": chain["psi"], "y": y_out},
    }
