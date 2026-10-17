"""Second derivative of the Digamma-family cumulant.

Translated from statmod 1.5.2 ``d2cumulant.digamma`` in ``R/digammaf.R``.
"""

from __future__ import annotations

import numpy as np


def d2cumulant_digamma(theta):
    """Variance (second cumulant derivative) at canonical parameter ``theta``."""
    theta = np.asarray(theta, dtype=float)
    out = 2.0 * (1.0 / theta + _trigamma(-theta))
    min_theta = float(np.min(theta))
    if min_theta < -1e3:
        large = theta < -1e3
        out = np.asarray(out, dtype=float)
        out[large] = (1.0 - 1.0 / (3.0 * theta[large])) / theta[large] ** 2
    return np.asarray(out, dtype=float)


def _trigamma(x):
    x = np.asarray(x, dtype=float)
    out = np.empty(x.shape, dtype=float)
    for idx, xi in np.ndenumerate(x):
        out[idx] = _trigamma_scalar(float(xi))
    return out


def _trigamma_scalar(x):
    if x <= 0:
        return np.nan
    from statmod.canonic_digamma import _logmdigamma

    def digamma(z):
        return np.log(z) - _logmdigamma(z)

    tail = 0.0
    z = x
    while z < 10.0:
        tail += 1.0 / z**2
        z += 1.0
    step = max(z * 1e-5, 1e-8)
    return tail + (digamma(z + step) - digamma(z - step)) / (2.0 * step)
