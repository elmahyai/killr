"""Centres of the hexagon grid. Ported from hexbin 1.28.6 `hgridcent` in R/hexutil.R."""

from __future__ import annotations

import math

import numpy as np

from ._r import r_colon_count


def hgridcent(xbins, xbnds, ybnds, shape, edge_add=0) -> dict:
    """Return `{"x", "y", "dimen", "dx", "dy"}` for every cell of the grid.

    `edge_add` widens the grid by that many cells on each side, as R's `edge.add` does.
    `dimen` is not truncated, as in R; the cell count follows R's `1:n` rule.
    """
    xb = np.asarray(xbnds, dtype=np.float64)
    yb = np.asarray(ybnds, dtype=np.float64)

    jmax = math.floor(xbins + 1.5001)
    c1 = 2 * math.floor((xbins * shape) / math.sqrt(3) + 1.5001)
    imax = (jmax * c1 - 1) / jmax + 1
    dimen = np.array([imax, float(jmax)], dtype=np.float64)

    c3 = (xb[1] - xb[0]) / xbins
    c4 = ((yb[1] - yb[0]) * math.sqrt(3)) / (2 * shape * xbins)
    if edge_add > 0:
        xb = xb + 1.5 * np.array([-edge_add * c3, edge_add * c3])
        yb = yb + np.array([-edge_add * c4, edge_add * c4])
        dimen = dimen + 2 * edge_add

    jmax = dimen[1]
    count = r_colon_count(dimen[0] * dimen[1])
    cell = np.arange(1, count + 1, dtype=np.float64)
    i = np.floor(cell / jmax)
    j = cell - i * jmax
    y = c4 * i + yb[0]
    x = c3 * np.where(i % 2 == 0, j, j + 0.5) + xb[0]
    return {"x": x, "y": y, "dimen": dimen, "dx": c3, "dy": c4}
