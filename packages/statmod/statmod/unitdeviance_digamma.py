"""Unit deviance for the Digamma GLM family.

Translated from statmod 1.5.2 ``unitdeviance.digamma`` in ``R/digammaf.R``.
"""

from __future__ import annotations

import numpy as np

from statmod.canonic_digamma import canonic_digamma
from statmod.cumulant_digamma import cumulant_digamma


def unitdeviance_digamma(y, mu):
    """Digamma-family unit deviance ``d(y, mu)`` for responses ``y`` and means ``mu``."""
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    thetay = canonic_digamma(y)
    theta = canonic_digamma(mu)
    return np.asarray(
        2.0
        * (
            y * (thetay - theta)
            - (cumulant_digamma(thetay) - cumulant_digamma(theta))
        ),
        dtype=float,
    )
