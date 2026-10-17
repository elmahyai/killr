"""Huber psi for robust regression (MASS psi.huber)."""

from __future__ import annotations

import numpy as np


def psi_huber(u, k: float = 1.345, deriv: int = 0):
    u_arr = np.asarray(u, dtype=float)
    if deriv:
        return (np.abs(u_arr) <= k).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.minimum(1.0, k / np.abs(u_arr))
    out = np.where(np.isfinite(out), out, 1.0)
    return out
