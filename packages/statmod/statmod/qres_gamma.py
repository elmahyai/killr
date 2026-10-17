"""Quantile residuals for gamma GLMs.

Translated from statmod 1.5.2 ``qres.gamma`` in ``R/qres.R``.
"""

from __future__ import annotations

import numpy as np

from statmod.pinvgauss import _pgamma_log
from statmod.qinvgauss import _qnorm_logp


def qres_gamma(glm_obj, dispersion=None):
    """Quantile residuals for a fitted gamma ``glm`` object."""
    mu = np.asarray(glm_obj["fitted_values"], dtype=float).reshape(-1)
    y = np.asarray(glm_obj["y"], dtype=float).reshape(-1)
    df = float(glm_obj["df_residual"])
    prior = glm_obj.get("prior_weights")
    if prior is None:
        w = 1.0
    else:
        w = np.asarray(prior, dtype=float).reshape(-1)

    if dispersion is None:
        dispersion = float(np.sum(w * ((y - mu) / mu) ** 2) / df)

    q = (w * y) / mu / dispersion
    shape = w / dispersion
    logp = _pgamma_log(
        np.asarray(q, dtype=np.float64),
        np.asarray(shape, dtype=np.float64),
        1.0,
        lower_tail=True,
    )
    return _qnorm_logp(logp, lower_tail=True)
