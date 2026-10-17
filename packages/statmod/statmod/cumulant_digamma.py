"""Cumulant function for the Digamma GLM family.

Translated from statmod 1.5.2 ``cumulant.digamma`` in ``R/digammaf.R``.
"""

from __future__ import annotations

import math

import numpy as np

_lgamma = np.frompyfunc(math.lgamma, 1, 1)


def cumulant_digamma(theta):
    """Digamma-family cumulant ``K(theta)`` at canonical parameter ``theta``."""
    theta = np.asarray(theta, dtype=float)
    neg_theta = -theta
    out = 2.0 * (
        theta * (np.log(neg_theta) - 1.0)
        + _lgamma(neg_theta).astype(float, copy=False)
    )
    return np.asarray(out, dtype=float)
