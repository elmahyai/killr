"""pan 2.0 pan.bd(): the R wrapper's index work, then the mgibbsbd kernel from pan_mgibbs.

The sampler is the Rust port of mgibbsbd in pan.f (crates/pan_mgibbs). psi is block
diagonal: one q x q block per response column. This wrapper does what pan.bd does
before the call: the checks, the indexes, the hyperparameter vector, and the output shape.
"""

import numpy as np
import pan_mgibbs

from pan._index import as_pred, as_response, hyp_bd, kernel_y, missing_patterns


def pan_bd(y, subj, pred, xcol, zcol, prior, seed, iter=1, start=None):
    """Gibbs sampler for the multivariate linear mixed model with block-diagonal psi.

    xcol and zcol are 1-based column numbers of pred, as in R. prior holds a, Binv, c
    (length r) and Dinv (q x q x r). start, when given, holds beta, sigma, psi (q x q x r)
    and y (the eps). Returns a dict with beta (p x r x iter), sigma (r x r x iter),
    psi (q x q x r x iter), y (the imputed response) and last (the final state).
    """
    y = as_response(y)
    pred = as_pred(pred)
    if np.isnan(pred).any():
        raise ValueError("missing values in pred not allowed")
    subj = np.asarray(subj, dtype=np.int64).ravel()
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

    pan_mgibbs.rngs(int(seed))  # rngs before the sampler, as pan.bd does
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
