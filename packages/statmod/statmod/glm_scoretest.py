"""Score test for adding covariates to a GLM.

Translated from statmod 1.5.2 ``glm.scoretest`` in ``R/glmscoretest.R``.
"""

from __future__ import annotations

import numpy as np


def _qr_resid(qr: dict, y: np.ndarray) -> np.ndarray:
    """Residuals from R ``qr.resid`` on a glm ``$qr`` object."""
    if "x" not in qr:
        raise ValueError("fit qr must include design matrix 'x' from R qr.X(qr)")
    x = np.asarray(qr["x"], dtype=float)
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    q_factor, _r = np.linalg.qr(x, mode="reduced")
    return y - q_factor @ (q_factor.T @ y)


def _family_name(family) -> str:
    if isinstance(family, dict):
        return str(family.get("family", family.get("name", "")))
    return str(family)


def glm_scoretest(fit, x2, dispersion=None):
    """Return score-test z-statistics for covariates ``x2`` given a glm fit."""
    w = np.asarray(fit["weights"], dtype=float).reshape(-1)
    r = np.asarray(fit["residuals"], dtype=float).reshape(-1)
    x2 = np.asarray(x2, dtype=float)
    if x2.ndim == 1:
        x2 = x2.reshape(-1, 1)
    elif x2.ndim == 0:
        x2 = x2.reshape(-1, 1)

    if np.any(w <= 0):
        keep = w > 0
        r = r[keep]
        x2 = x2[keep, :]
        w = w[keep]

    if dispersion is None:
        fam = _family_name(fit["family"])
        if fam in ("poisson", "binomial"):
            dispersion = 1.0
        else:
            df_res = int(fit["df_residual"])
            if df_res > 0:
                dispersion = float(np.sum(w * r * r) / df_res)
            else:
                raise ValueError("No residual df available to estimate dispersion")

    ws = np.sqrt(w)
    x2_w = ws[:, None] * x2
    x2_1w = _qr_resid(fit["qr"], x2_w)
    zw = ws * r
    numer = np.sum(x2_1w * zw[:, None], axis=0)
    denom = np.sqrt(np.sum(x2_1w * x2_1w, axis=0))
    return numer / denom / np.sqrt(float(dispersion))
