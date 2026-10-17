"""Create polarLAB color objects (colorspace 2.1-4)."""

from __future__ import annotations

import numpy as np

_MISSING = object()


class PolarLABColor:
    """Coordinates of one or more colors in polar CIE L*a*b* space."""

    __slots__ = ("space", "coords", "names", "columns")

    def __init__(self, coords, names):
        self.space = "polarLAB"
        self.coords = np.asarray(coords, dtype=np.float64)
        self.names = names
        self.columns = ("L", "C", "H")

    def __str__(self):
        return str(self.coords)


def polarLAB(L=_MISSING, C=_MISSING, H=_MISSING, names=_MISSING):
    """Build a polarLAB color from lightness, chroma, and hue coordinates."""
    if L is _MISSING:
        return PolarLABColor(np.zeros((0, 0), dtype=np.float64), None)
    if isinstance(L, tuple) and len(L) == 2 and not isinstance(L[0], (str, bytes)):
        values, embedded_names = L
        if names is _MISSING:
            names = embedded_names
    else:
        values = L
    arr = np.asarray(values, dtype=np.float64)
    row_names = None if names is _MISSING or names is None else tuple(str(n) for n in names)
    if C is _MISSING and H is _MISSING:
        coords = arr
        if coords.ndim != 2 or coords.shape[1] != 3:
            raise ValueError("invalid color matrix")
    else:
        n = arr.size if arr.ndim == 1 else arr.shape[0]
        def recycle(value):
            out = np.asarray(value, dtype=np.float64).ravel()
            if out.size == 1:
                return np.full(n, out[0])
            if out.size != n:
                raise ValueError("invalid color matrix")
            return out
        coords = np.column_stack([recycle(arr), recycle(C), recycle(H)])
    if coords.dtype.kind != "f" or coords.size < 1:
        raise ValueError("invalid color matrix")
    return PolarLABColor(coords, row_names)
