"""R helpers `.na.to.snglcode`, `.na.to.icode` and `.code.to.na` of mix 1.0-13.

Each returns a new array. The values stay floats, and integer codes are whole numbers,
so the Fortran wrappers can copy them into int32 arrays exactly.
"""

from __future__ import annotations

import numpy as np


def na_to_snglcode(x, mvcode) -> np.ndarray:
    """`x[is.na(x)] <- mvcode`, with the code kept as a double."""
    x = np.array(x, dtype=float, copy=True)
    x[np.isnan(x)] = float(mvcode)
    return x


def na_to_icode(x, mvcode) -> np.ndarray:
    """`x[is.na(x)] <- as.integer(mvcode)`."""
    x = np.array(x, dtype=float, copy=True)
    x[np.isnan(x)] = float(int(mvcode))
    return x


def code_to_na(x, mvcode) -> np.ndarray:
    """`x[x == mvcode] <- NA`."""
    x = np.array(x, dtype=float, copy=True)
    x[x == float(mvcode)] = np.nan
    return x
