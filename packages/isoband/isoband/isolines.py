"""Isolines of a grid, as R's ``isolines()`` in isoband 0.3.0.

``z`` is a matrix with one row per ``y`` value and one column per ``x`` value.
Each level gives a dict with ``x``, ``y``, and ``id`` arrays. Each ``id`` is one
line, in the order R produces. Cells that touch a non-finite value (NA or NaN) are
skipped.
"""

from __future__ import annotations

import numpy as np
from isoband_kernel import isolines_kernel


def isolines(x, y, z, levels) -> list[dict[str, np.ndarray]]:
    x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    z_arr = np.asarray(z, dtype=np.float64)
    if z_arr.ndim != 2:
        raise ValueError("z must be a matrix with one row per y and one column per x")
    nrow, ncol = z_arr.shape
    levels_arr = np.asarray(levels, dtype=np.float64).reshape(-1)
    # R stores matrices column-major; the kernel reads the same layout.
    z_flat = np.ravel(z_arr, order="F")
    out = isolines_kernel(x_arr, y_arr, z_flat, nrow, ncol, levels_arr)
    return [{"x": xs, "y": ys, "id": ids} for xs, ys, ids in out]
