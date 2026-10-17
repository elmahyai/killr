"""Simulate color vision deficiency from a transform matrix (colorspace 2.1-4)."""

from __future__ import annotations

import numpy as np

from colorspace.deutan import _simulate_cvd


def simulate_cvd(col, cvd_transform, linear=True):
    """Apply a 3 by 3 CVD matrix to colors.

    Hex colors and color names are linearized before the matrix when ``linear``
    is true, then mapped back to gamma-corrected sRGB. A matrix with R, G, and
    B in ``[0, 255]`` is transformed directly. A color object is converted to
    RGB or sRGB, transformed, and returned in its original space.
    """
    transform = np.asarray(cvd_transform, dtype=np.float64)
    if transform.shape != (3, 3):
        raise ValueError("cvd_transform must be a 3x3 matrix")
    return _simulate_cvd(col, transform, linear=bool(linear))
