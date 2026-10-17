"""Mean value function for the Digamma GLM family.

Translated from statmod 1.5.2 ``meanval.digamma`` in ``R/digammaf.R``.
"""

from __future__ import annotations

import numpy as np

from statmod.logmdigamma import logmdigamma


def meanval_digamma(theta):
    """Digamma-family mean ``E[Y]`` at canonical parameter ``theta``."""
    theta = np.asarray(theta, dtype=float)
    return 2.0 * logmdigamma(-theta)
