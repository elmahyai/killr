"""pan 2.0 mgibbs(): the R-side work before the Fortran routine mgibbs, then the kernel.

In R, pan() checks pred, builds the missing-data indexes (patt, rmat, iposn, pstfin), packs
the hyperparameters a, Binv, c and Dinv into hyp, seeds the generator with rngs, calls
.Fortran("mgibbs", ...), and shapes the output list. This module does the same work in
Python and calls the Rust port of mgibbs in pan.f (crates/pan_mgibbs).
"""

import numpy as np
import pan_mgibbs

from pan._index import as_pred, as_response, hyp_full, kernel_y, missing_patterns


def mgibbs(y, subj, pred, xcol, zcol, prior, seed, iter=1, start=None):
    """Gibbs sampler for the multivariate linear mixed model with a full psi (rq x rq).

    xcol and zcol are 1-based column numbers of pred, as in R. prior holds a, Binv, c and
    Dinv (rq x rq). start, when given, holds beta, sigma, psi and y (the starting eps).
    Returns a dict with beta (p x r x iter), sigma (r x r x iter), psi (rq x rq x iter),
    y (the imputed response) and last (the final state: beta, sigma, psi, y).
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
    rq = r * q

    patt, rmat, iposn, pstfin, _ = missing_patterns(y)
    hyp = hyp_full(prior, r, q)

    if start is None:
        sflag, beta, sigma, psi, eps = 0, None, None, None, None
    else:
        sflag = 1
        beta = np.asarray(start["beta"], dtype=float)
        sigma = np.asarray(start["sigma"], dtype=float)
        psi = np.asarray(start["psi"], dtype=float)
        eps = as_response(start["y"])

    pan_mgibbs.rngs(int(seed))  # rngs before the sampler, as pan() does
    chain = pan_mgibbs.mgibbs(
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


def _check_contiguous(subj):
    """The Fortran istfin needs each subject in one block of rows, as R's m assumes."""
    if subj.size == 0:
        raise ValueError("subj must not be empty")
    runs = 1 + int(np.count_nonzero(subj[1:] != subj[:-1]))
    if runs != np.unique(subj).size:
        raise ValueError("subj must label each subject in one contiguous block of rows")
