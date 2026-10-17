"""Random draws that follow R's nmath on boot's Mersenne-Twister.

norm_rand is the Inversion kind: two uniforms packed into 27 bits, then
qnorm. exp_rand is Ahrens-Dieter, not -log(unif).
"""

import math

from boot.rng import unif
from scipy.stats import norm

_BIG = 134217728  # 2^27
_EXP_Q = (
    0.6931471805599453,
    0.9333736875190459,
    0.9888777961838675,
    0.9984959252914960,
    0.9998292811061389,
    0.9999833164100727,
    0.9999985691438767,
    0.9999998906925558,
    0.9999999924734159,
    0.9999999995283275,
    0.9999999999728814,
    0.9999999999985598,
    0.9999999999999289,
    0.9999999999999968,
    0.9999999999999999,
    1.0000000000000000,
)


def qnorm(p, mean=0.0, sd=1.0, lower_tail=True, log_p=False):
    """R qnorm. SciPy's ppf matched R 4.5 on the tails used here."""
    if log_p:
        p = math.exp(p)
    if not lower_tail:
        p = 1.0 - p
    if sd < 0 or not math.isfinite(sd) or not 0.0 <= p <= 1.0:
        return math.nan
    if sd == 0:
        return mean
    return float(norm.ppf(p)) * sd + mean


def norm_rand():
    """One standard normal, R's default Inversion kind."""
    u1 = unif()
    u1 = int(_BIG * u1) + unif()
    return qnorm(u1 / _BIG)


def exp_rand():
    """One standard exponential, Ahrens-Dieter."""
    q = _EXP_Q
    a = 0.0
    u = unif()
    while u <= 0.0 or u >= 1.0:
        u = unif()
    while True:
        u += u
        if u > 1.0:
            break
        a += q[0]
    u -= 1.0
    if u <= q[0]:
        return a + u
    i = 0
    ustar = unif()
    umin = ustar
    while True:
        ustar = unif()
        if umin > ustar:
            umin = ustar
        i += 1
        if u <= q[i]:
            break
    return a + umin * q[0]


def runif(a=0.0, b=1.0):
    """R runif for a finite interval. One unif_rand."""
    if not math.isfinite(a) or not math.isfinite(b) or b < a:
        return math.nan
    if a == b:
        return a
    return a + (b - a) * unif()


def rng_sign():
    return 1.0 if unif() > 0.5 else -1.0
