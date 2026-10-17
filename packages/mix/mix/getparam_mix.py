"""`getparam.mix` of mix 1.0-13 (R/mix.R): the parameters on the original scale.

This is array arithmetic on the estimate, with no kernel. The cell probabilities are
returned in the array shape of the contingency table, the means and the covariance on
the scale of the continuous columns. With `corr=True`, the standard deviations and the
correlation matrix are returned instead of the covariance.
"""

from __future__ import annotations

import numpy as np

from .em_mix import Theta
from .prelim_mix import MixData


def getparam_mix(s: MixData, theta: Theta, corr: bool = False) -> dict:
    q = int(s.q)
    d = tuple(int(v) for v in np.asarray(s.d).ravel())
    pi_flat = np.asarray(theta.pi, dtype=float).ravel()
    pii = pi_flat.reshape(d, order="F")
    sdv_scale = np.asarray(s.sdv, dtype=float).ravel()
    xbar = np.asarray(s.xbar, dtype=float).ravel()

    mu = np.asarray(theta.mu, dtype=float) * sdv_scale[:, None] + xbar[:, None]
    mu[:, pi_flat == 0] = np.nan

    psi = np.asarray(s.psi, dtype=int)
    sigma = np.asarray(theta.sigma, dtype=float)[psi - 1]
    tmp = np.tile(sdv_scale[:, None], (1, q))
    sigma = sigma * tmp * tmp.T

    if corr:
        sdv = np.sqrt(np.diag(sigma))
        tmp = np.tile(sdv[:, None], (1, q))
        r = sigma / (tmp * tmp.T)
        return {"pi": pii, "mu": mu, "sdv": sdv, "r": r}
    return {"pi": pii, "mu": mu, "sigma": sigma}
