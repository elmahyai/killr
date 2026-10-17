"""Hampel psi for robust regression (MASS psi.hampel)."""

from __future__ import annotations

import numpy as np


def psi_hampel(u, a: float = 2, b: float = 4, c: float = 8, deriv: int = 0):
    u_arr = np.asarray(u, dtype=float)
    abs_u = np.abs(u_arr)
    u_cap = np.minimum(abs_u + 1e-50, c)
    if deriv:
        return np.where(
            abs_u <= c,
            np.where(u_cap <= a, 1.0, np.where(u_cap <= b, 0.0, -a / (c - b))),
            0.0,
        )
    num = np.where(
        u_cap <= a,
        u_cap,
        np.where(u_cap <= b, a, a * (c - u_cap) / (c - b)),
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / u_cap
    return out
