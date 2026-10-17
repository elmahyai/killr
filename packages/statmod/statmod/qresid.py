"""Dispatch quantile residuals by GLM family.

Translated from statmod 1.5.2 ``qresid`` / ``qresiduals`` in ``R/qres.R``.
"""

from __future__ import annotations

from statmod.qres_binom import qres_binom
from statmod.qres_default import qres_default
from statmod.qres_gamma import qres_gamma
from statmod.qres_invgauss import qres_invgauss
from statmod.qres_nbinom import qres_nbinom
from statmod.qres_pois import qres_pois
from statmod.qres_tweedie import qres_tweedie


def qresid(glm_obj, dispersion=None):
    """Quantile residuals for a fitted ``glm`` object."""
    glm_family = glm_obj["family"]["family"]
    if glm_family[:17] == "Negative Binomial":
        glm_family = "nbinom"
    if glm_family == "binomial":
        return qres_binom(glm_obj)
    if glm_family == "poisson":
        return qres_pois(glm_obj)
    if glm_family == "Gamma":
        return qres_gamma(glm_obj, dispersion)
    if glm_family == "inverse.gaussian":
        return qres_invgauss(glm_obj, dispersion)
    if glm_family == "Tweedie":
        return qres_tweedie(glm_obj, dispersion)
    if glm_family == "nbinom":
        return qres_nbinom(glm_obj)
    return qres_default(glm_obj, dispersion)


qresiduals = qresid
