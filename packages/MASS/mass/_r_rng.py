"""R set.seed and Inversion rnorm for MASS mvrnorm.

Uses boot's Mersenne-Twister and qnorm so draws match set.seed in R checks.
"""

from __future__ import annotations

from boot.rng import set_seed, unif
from boot.series import qnorm

_BIG = 134217728


def norm_rand() -> float:
    """One standard normal, R's default Inversion kind."""
    u1 = unif()
    u1 = int(_BIG * u1) + unif()
    return qnorm(u1 / _BIG)
