"""pan 2.0 pan(): the R wrapper's index work, then the mgibbs kernel from pan_mgibbs.

The sampler is the Rust port of mgibbs in pan.f (crates/pan_mgibbs). This wrapper does
what pan.R does before the call: it checks pred, builds the missing-data indexes and
the hyperparameter vector, seeds the generator, and shapes the output as R does.
"""

import numpy as np
import pan_mgibbs

from pan._index import as_pred, as_response, hyp_full, kernel_y, missing_patterns


def pan(y, subj, pred, xcol, zcol, prior, seed, iter=1, start=None):
    """Gibbs sampler for the multivariate linear mixed model with a full psi.

    xcol and zcol are 1-based column numbers of pred, as in R. prior holds a, Binv, c
    and Dinv (rq x rq). start, when given, holds beta, sigma, psi and y (the eps).
    Returns a dict with beta (p x r x iter), sigma (r x r x iter), psi (rq x rq x iter),
    y (the imputed response) and last (the final state).
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

    pan_mgibbs.rngs(int(seed))  # rngs before the sampler, as pan.R does
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
