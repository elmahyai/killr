"""Variance function for the Digamma GLM family.

Translated from statmod 1.5.2 ``varfun.digamma`` in ``R/digammaf.R``.
"""

from __future__ import annotations

import numpy as np

from statmod.canonic_digamma import canonic_digamma
from statmod.d2cumulant_digamma import _trigamma


def varfun_digamma(mu):
    """GLM variance at positive mean ``mu`` via the canonical parameter."""
    mu = np.asarray(mu, dtype=float)
    theta = canonic_digamma(mu)
    return np.asarray(2.0 * (1.0 / theta + _trigamma(-theta)), dtype=float)
