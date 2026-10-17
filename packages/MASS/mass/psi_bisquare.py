"""Bisquare psi for robust regression (MASS psi.bisquare)."""

from __future__ import annotations

import numpy as np


def psi_bisquare(u, c: float = 4.685, deriv: int = 0):
    u_arr = np.asarray(u, dtype=float)
    if deriv:
        t = (u_arr / c) ** 2
        return np.where(t < 1, (1 - t) * (1 - 5 * t), 0.0)
    abs_u = np.abs(u_arr)
    ratio = np.minimum(1.0, abs_u / c)
    return (1.0 - ratio**2) ** 2
