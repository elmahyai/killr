"""Log minus digamma function.

Translated from statmod 1.5.2 ``logmdigamma`` in ``R/digamma.R``.
"""

from __future__ import annotations

import numpy as np


def logmdigamma(x):
    """``log(x) - digamma(x)`` without subtractive cancellation for large ``x``."""
    z = np.asarray(x)
    if z.size == 0:
        return z.copy()
    return _logmdigamma(z)


def _logmdigamma(z):
    omit = np.isnan(z) | (np.real(z) <= 0)
    if np.any(omit):
        out = np.array(z, copy=True, dtype=np.result_type(z, 0.0))
        out[omit] = np.nan
        if np.any(~omit):
            out[~omit] = _logmdigamma(z[~omit])
        return out
    small = np.abs(z) < 5
    if np.any(small):
        out = np.empty_like(z, dtype=np.result_type(z, 1.0))
        xs = z[small]
        out[small] = (
            np.log(xs / (xs + 5))
            + _logmdigamma(xs + 5)
            + 1.0 / xs
            + 1.0 / (xs + 1)
            + 1.0 / (xs + 2)
            + 1.0 / (xs + 3)
            + 1.0 / (xs + 4)
        )
        if np.any(~small):
            out[~small] = _logmdigamma(z[~small])
        return out
    return _logmdigamma_asymptotic(z)


def _logmdigamma_asymptotic(z):
    x = 1.0 / z**2
    tail = x * (
        -1.0 / 12.0
        + (
            x
            * (
                1.0 / 120.0
                + (
                    x
                    * (
                        -1.0 / 252.0
                        + (
                            x
                            * (
                                1.0 / 240.0
                                + (
                                    x
                                    * (
                                        -1.0 / 132.0
                                        + (
                                            x
                                            * (
                                                691.0 / 32760.0
                                                + (x * (-1.0 / 12.0 + (3617.0 * x) / 8160.0))
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )
    return 1.0 / (2.0 * z) - tail
