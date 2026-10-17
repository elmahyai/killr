"""M scale estimation.

Translated from statmod 1.5.2 ``mscale`` in ``R/mscale.R``.
"""

from __future__ import annotations

import warnings

import numpy as np


def _rho_hampel(u, a=1.5, b=3.5, c=8):
    u = np.asarray(u, dtype=np.float64)
    abs_u = np.abs(u)
    increasing = abs_u <= a
    flat = (abs_u > a) & (abs_u <= b)
    descending = (abs_u > b) & (abs_u <= c)
    zero = abs_u > c
    rho = abs_u.copy()
    rho[increasing] = (abs_u[increasing] * abs_u[increasing]) / 2
    rho[flat] = a * (abs_u[flat] - a / 2)
    rho[descending] = a * (b - a / 2) + a * (abs_u[descending] - b) * (
        1 - (abs_u[descending] - b) / (c - b) / 2
    )
    rho[zero] = (a * (b - a + c)) / 2
    return rho


def _psi_hampel(u, a=1.5, b=3.5, c=8):
    u = np.asarray(u, dtype=np.float64)
    abs_u = np.abs(u)
    flat = (abs_u > a) & (abs_u <= b)
    descending = (abs_u > b) & (abs_u <= c)
    zero = abs_u > c
    psi = u.copy()
    psi[flat] = np.sign(u[flat]) * a
    psi[descending] = np.sign(u[descending]) * a * (c - abs_u[descending]) / (c - b)
    psi[zero] = 0
    return psi


def mscale(u, na_rm=False):
    """Robust scale estimate from residuals using Hampel's redescending psi."""
    values = np.asarray(u, dtype=np.float64).reshape(-1)
    is_na = np.isnan(values)
    if np.any(is_na):
        if na_rm:
            if np.any(~is_na):
                values = values[~is_na]
            else:
                return np.nan
        else:
            return np.nan

    if np.mean(values == 0) >= 0.5:
        return 0.0

    abs_values = np.abs(values)
    scale = np.median(abs_values) / 0.6744898
    iteration = 0
    while True:
        iteration += 1
        z = values / 0.212 / scale
        d1 = np.mean(_rho_hampel(z)) - 3.75
        d2 = np.mean(z * _psi_hampel(z))
        scale = scale * (1 + d1 / d2)
        if iteration > 50:
            warnings.warn("Max iterations exceeded", RuntimeWarning, stacklevel=2)
            break
        if abs(d1 / d2) < 1e-13:
            break
    return float(scale)
