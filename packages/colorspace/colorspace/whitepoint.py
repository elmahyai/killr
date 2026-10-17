"""Get or set the colorspace global whitepoint."""

from __future__ import annotations

import numpy as np

from colorspace.xyz import XYZ, XYZColor

_DEFAULT = np.array([[95.047, 100.0, 108.883]], dtype=np.float64)
_WHITE = _DEFAULT.copy()
_MISSING = object()


def whitepoint(white=_MISSING, *args):
    """Get the current XYZ whitepoint, or set it and return the new value."""
    global _WHITE
    if white is _MISSING and not args:
        return XYZ(_WHITE.copy())
    if white is None:
        values = _DEFAULT.copy()
    elif isinstance(white, XYZColor):
        values = np.asarray(white.coords, dtype=np.float64)
    else:
        values = np.asarray([white, *args], dtype=np.float64)
        if values.size != 3:
            values = np.asarray(white, dtype=np.float64)
        if values.ndim == 1 and values.size == 3:
            values = values.reshape(1, 3)
        elif values.ndim == 2 and values.shape[1] != 3:
            values = values.T
    if values.ndim != 2 or values.shape[1] != 3:
        raise ValueError("'white' needs to be a 3-dimensional XYZ specification")
    _WHITE = values[:1].copy()
    return XYZ(_WHITE.copy())
