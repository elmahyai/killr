"""Quantile residuals for inverse Gaussian GLMs.

Translated from statmod 1.5.2 ``qres.invgauss`` in ``R/qres.R``.
"""

from __future__ import annotations

import numpy as np

from statmod.pinvgauss import pinvgauss
from statmod.qinvgauss import _qnorm_logp


def qres_invgauss(glm_obj, dispersion=None):
    """Quantile residuals for a fitted inverse Gaussian ``glm`` object."""
    mu = np.asarray(glm_obj["fitted_values"], dtype=float).reshape(-1)
    y = np.asarray(glm_obj["y"], dtype=float).reshape(-1).copy()
    df = float(glm_obj["df_residual"])
    prior = glm_obj.get("prior_weights")
    if prior is None:
        w = 1.0
    else:
        w = np.asarray(prior, dtype=float).reshape(-1)

    if dispersion is None:
        dispersion = float(np.sum(w * (y - mu) ** 2 / (mu**2 * y)) / df)

    up = y > mu
    down = y < mu
    if np.any(down):
        logp = pinvgauss(
            y[down],
            mean=mu[down],
            dispersion=dispersion,
            lower_tail=True,
            log_p=True,
        )
        y[down] = _qnorm_logp(np.asarray(logp, dtype=np.float64), lower_tail=True)
    if np.any(up):
        logp = pinvgauss(
            y[up],
            mean=mu[up],
            dispersion=dispersion,
            lower_tail=False,
            log_p=True,
        )
        y[up] = _qnorm_logp(np.asarray(logp, dtype=np.float64), lower_tail=False)
    return y
