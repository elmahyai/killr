"""Hexagon outlines around points. Ported from hexbin 1.28.6 `hexpolygon` in R/grid.hexagons.R.

R draws with grid.polygon() when the hexagon template has no separator, and with polygon()
when it does. This port computes the same vertex lists. With `ax` it also draws them with
Matplotlib. The R colour indices of `fill` and `border` are not mapped; pass Matplotlib colours.
"""

from __future__ import annotations

import numpy as np

from .hexcoords import hexcoords


def hexpolygon(
    x,
    y,
    hexC: dict | None = None,
    dx: float | None = None,
    dy: float | None = None,
    ax=None,
    facecolor=None,
    edgecolor=None,
) -> dict:
    """Return the vertices of one hexagon around each `(x[i], y[i])`.

    The result is `{"x", "y", "id_lengths"}`. `id_lengths` is the vertex count per hexagon, as
    R's `id.lengths`. With a separator in `hexC` (R's `no.sep = FALSE`), the separator entries
    are kept as NaN, and no `id_lengths` is needed. `hexC` must describe one hexagon, so its
    length is 6 (no separator) or 7 (with one). If `hexC` is None, it is `hexcoords(dx, dy)`.
    """
    xs = np.asarray(x, dtype=np.float64).ravel()
    ys = np.asarray(y, dtype=np.float64).ravel()
    n = xs.size
    if ys.size != n:
        raise ValueError("length(y) == n is not TRUE")
    if hexC is None:
        if dx is None:
            raise ValueError('argument "dx" is missing, with no default')
        hexC = hexcoords(dx, dy, n=1)
    hx = np.asarray(hexC["x"], dtype=np.float64)
    hy = np.asarray(hexC["y"], dtype=np.float64)
    k = hx.size
    if k not in (6, 7):
        raise ValueError("hexC must describe one hexagon: 6 vertices, or 7 with a separator")
    # R: rep.int(hexC$x, n) + rep.int(x, n6), with n6 the per-hexagon vertex count.
    out_x = np.tile(hx, n) + np.repeat(xs, k)
    out_y = np.tile(hy, n) + np.repeat(ys, k)
    result = {"x": out_x, "y": out_y, "id_lengths": np.full(n, k, dtype=np.int64)}
    if hexC.get("no_sep", True) is False:
        del result["id_lengths"]
    if ax is not None:
        _draw(ax, result, facecolor, edgecolor)
    return result


def _draw(ax, result: dict, facecolor, edgecolor) -> None:
    """Draw the vertex lists as polygons. Separator NaNs split the hexagons."""
    from matplotlib.collections import PolyCollection

    pts = np.column_stack([result["x"], result["y"]])
    polys = []
    if "id_lengths" in result:
        # grid.polygon with id.lengths: one polygon per hexagon.
        start = 0
        for k in result["id_lengths"].tolist():
            polys.append(pts[start : start + k])
            start += k
    else:
        # polygon() with NA separators: a NaN row ends the current polygon.
        current: list = []
        for p in pts:
            if np.isnan(p).any():
                if len(current) >= 3:
                    polys.append(np.asarray(current))
                current = []
            else:
                current.append(p)
        if len(current) >= 3:
            polys.append(np.asarray(current))
    coll = PolyCollection(polys, facecolors=facecolor, edgecolors=edgecolor)
    ax.add_collection(coll)
    ax.autoscale_view()
