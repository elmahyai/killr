"""Extract coordinate matrices from color objects (colorspace 2.1-4)."""

from __future__ import annotations

import numpy as np


def coords(color):
    """Return the coordinate matrix of a colorspace color object."""
    matrix = np.asarray(color.coords, dtype=np.float64)
    if matrix.size == 0:
        return matrix.reshape(0, 0)
    return matrix.copy()
