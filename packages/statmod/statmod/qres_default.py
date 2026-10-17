"""Quantile residuals for Gaussian and default GLMs.

Translated from statmod 1.5.2 ``qres.default`` in ``R/qres.R``.
"""

from __future__ import annotations

import warnings

import numpy as np


def qres_default(glm_obj, dispersion=None):
    """Quantile residuals from deviance residuals and dispersion."""
    r = np.asarray(glm_obj["deviance_residuals"], dtype=float).reshape(-1)
    if dispersion is None:
        df_r = float(glm_obj["df_residual"])
        if df_r > 0:
            weights = np.asarray(glm_obj["weights"], dtype=float).reshape(-1)
            working = np.asarray(glm_obj["working_residuals"], dtype=float).reshape(-1)
            if np.any(weights == 0):
                warnings.warn(
                    "observations with zero weight not used for calculating dispersion",
                    stacklevel=2,
                )
            dispersion = float(np.sum(weights * working**2) / df_r)
        else:
            dispersion = 1.0
    return r / np.sqrt(dispersion)
