"""Vertex offsets of one hexagon. Ported from hexbin 1.28.6 `hexcoords` in R/grid.hexagons.R."""

from __future__ import annotations

import math

import numpy as np


def hexcoords(dx, dy=None, n: int = 1, sep=None) -> dict:
    """Return `{"x": ..., "y": ..., "no_sep": ...}` for `n` hexagons.

    The six vertices are listed in R's order. With `sep` not None, a separator value is
    appended after each hexagon (`sep=np.nan` gives R's `NA`), and `no_sep` is False.
    R's `no.sep` is returned as `no_sep`.
    """
    dx_arr = np.asarray(dx, dtype=np.float64)
    if dx_arr.size != 1:
        raise ValueError("length(dx) == 1 is not TRUE")
    dxv = float(dx_arr)
    if dy is None:
        dyv = dxv / math.sqrt(3)
    else:
        dyv = float(dy)

    if sep is None:
        xs = np.array([dxv, dxv, 0.0, -dxv, -dxv, 0.0])
        ys = np.array([dyv, -dyv, -2 * dyv, -dyv, dyv, 2 * dyv])
        return {"x": np.tile(xs, n), "y": np.tile(ys, n), "no_sep": True}

    sepv = float(sep)
    xs = np.array([dxv, dxv, 0.0, -dxv, -dxv, 0.0, sepv])
    ys = np.array([dyv, -dyv, -2 * dyv, -dyv, dyv, 2 * dyv, sepv])
    return {"x": np.tile(xs, n), "y": np.tile(ys, n), "no_sep": False}
