"""Translate named locfit limits into a numeric vector."""

from __future__ import annotations

import numpy as np


def lflim(limits, nm, ret):
    names = list(nm)
    out = np.asarray(ret, dtype=float).copy()
    if isinstance(limits, (list, tuple, np.ndarray)) and not isinstance(limits, dict):
        return np.asarray(limits, dtype=float)
    d = len(names)
    for i, name in enumerate(names):
        if name in limits:
            value = np.asarray(limits[name], dtype=float).reshape(-1)
            out[i] = value[0]
            out[i + d] = value[-1]
    return out


__all__ = ["lflim"]
