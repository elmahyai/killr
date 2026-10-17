"""R semantics shared by the hexbin translations. Helper, not a translated function."""

from __future__ import annotations

import numpy as np

# R's NA_integer_ is the int32 minimum.
NA_INTEGER = -2147483648

# R adds FLT_EPSILON before truncating the length of `from:to`.
_FLT_EPSILON = 1.1920928955078125e-07


def r_colon_count(to: float) -> int:
    """Number of elements in R's `1:to` for `to >= 1` (non-integer `to` truncates)."""
    return int(abs(to - 1) + 1 + _FLT_EPSILON)


def add_bit(bnds, f: float) -> np.ndarray:
    """Port of the internal `addBit(bnds, f)` in smoothHexbin: bnds + c(-f, f) * diff(bnds)."""
    b = np.asarray(bnds, dtype=np.float64)
    return b + np.array([-f, f]) * (b[1] - b[0])


def encompass_fails(xbnds, rng) -> bool:
    """R: any(sign(xbnds - range(x)) == c(1, -1))."""
    s = np.sign(np.asarray(xbnds, dtype=np.float64) - np.asarray(rng, dtype=np.float64))
    return bool(s[0] == 1 or s[1] == -1)
