"""Jitter tied values with R's Mersenne-Twister, from the boot translation."""

from __future__ import annotations

import numpy as np

from boot.rng import unif


def dither(x, type="symmetric", value=None):
    """Add a uniform jitter. The draws are R's runif, so set the boot seed first."""
    values = np.asarray(x, dtype=float)
    if values.size == 0:
        return values.copy()
    if not np.issubdtype(np.asarray(x).dtype, np.number) and not _all_numeric(x):
        raise ValueError("'x' must be numeric")
    if value is None or (isinstance(value, (list, tuple)) and len(value) == 0):
        unique = np.unique(values)
        if unique.size < 2:
            raise ValueError("dither needs at least two distinct values when value is missing")
        value = float(np.min(np.diff(unique)))
    value = float(value)
    draws = np.array([unif() for _ in range(values.size)])
    if type == "symmetric":
        return values + (draws - 0.5) * value
    if type == "right":
        return values + draws * value
    raise ValueError("invalid type")


def _all_numeric(x):
    try:
        np.asarray(x, dtype=float)
    except (TypeError, ValueError):
        return False
    return True
