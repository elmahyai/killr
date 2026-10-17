"""clPairs and clPairsLegend: the classification scatter-plot matrix (mclust graphics.R).

The n-by-n panel layout is ``killplot.pairs_grid``, the frame of R's
``pairs()``. Each panel sets its limits as R's ``pairs()`` does, from the range
of its two variables extended by 4 per cent. The points inside each panel are
drawn by Matplotlib through ``PlotLog``.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from killplot import pairs_grid

from .mclust_options import mclust_options
from .plot_log import PlotLog, _as_char, class_levels

__all__ = ["clPairs", "clPairsLegend"]

_EXPAND = 0.04  # R's xaxs = "r" and yaxs = "r"


def _r_limits(values: Any) -> tuple[float, float]:
    """The axis limits R uses for one variable of a pairs panel."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    lo, hi = float(v.min()), float(v.max())
    if lo == hi:
        if lo == 0.0:
            lo, hi = -1.0, 1.0
        else:
            t = 0.4 * abs(lo)
            lo, hi = lo - t, hi + t
    span = hi - lo
    return lo - _EXPAND * span, hi + _EXPAND * span


def clPairs(
    data: Any,
    classification: Sequence[Any] | None = None,
    symbols: Sequence[Any] | None = None,
    colors: Sequence[str] | None = None,
    cex: Sequence[float] | float | None = None,
    gap: float = 0.2,
    grid: bool = False,
    *,
    fig: Any = None,
    ax: Any = None,
    log: PlotLog | None = None,
) -> dict[str, Any]:
    """Scatter-plot matrix of ``data`` coloured and marked by ``classification``.

    Two-column data is drawn as one plot on ``ax``. With more columns the
    panels go on ``fig`` through ``killplot.pairs_grid``; when ``fig`` is None
    the function only computes the values and draws nothing.
    """
    if log is None:
        log = PlotLog()
    X = np.asarray(data, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    n, d = X.shape
    if classification is None:
        classification = [1] * n
    chars, levels = class_levels(classification)
    l = len(levels)
    codes = np.array([levels.index(c) + 1 for c in chars], dtype=int)
    if len(codes) != n:
        raise ValueError("classification variable must have the same length as nrows of data!")
    opt_sym = list(mclust_options("classPlotSymbols"))
    opt_col = list(mclust_options("classPlotColors"))
    if symbols is None:
        if l == 1:
            symbols = ["."]
        if l <= len(opt_sym):
            symbols = opt_sym
        elif l <= 9:
            symbols = [str(i) for i in range(1, 10)]
        elif l <= 26:
            symbols = [chr(ord("A") + i) for i in range(l)]
        else:
            symbols = [16] * l
    symbols = list(symbols)
    if len(symbols) == 1:
        symbols = symbols * l
    if len(symbols) < l:
        symbols = [16] * l
    if colors is None and l <= len(opt_col):
        colors = opt_col[:l]
    colors = list(colors) if colors is not None else []
    if len(colors) == 1:
        colors = colors * l
    if len(colors) < l:
        colors = ["black"] * l
    if cex is None:
        cex = 1.0
    cex_v = [float(cex)] * l if np.ndim(cex) == 0 else list(np.asarray(cex, float))
    cex_v = (cex_v * l)[:l] if len(cex_v) == 1 else cex_v[:l]
    grid = bool(grid)

    pch_pt = [symbols[c - 1] for c in codes]
    col_pt = [colors[c - 1] for c in codes]

    if d > 2:
        axes = None
        if fig is not None:
            axes = pairs_grid(fig, d, gap=gap)
        for j in range(d):
            for i in range(d):
                if i == j:
                    continue
                x_j = X[:, j]
                y_i = X[:, i]
                panel_ax = None
                if axes is not None:
                    panel_ax = axes[i][j]
                    panel_ax.set_xlim(_r_limits(x_j))
                    panel_ax.set_ylim(_r_limits(y_i))
                log.panel = (i + 1, j + 1)
                log.points(panel_ax, x_j, y_i, pch_pt, col_pt)
        log.panel = (1, 1)
    elif d == 2:
        log.window(ax, (float(X[:, 0].min()), float(X[:, 0].max())),
                   (float(X[:, 1].min()), float(X[:, 1].max())))
        log.points(ax, X[:, 0], X[:, 1], pch_pt, col_pt)
    return {"d": d, "class": levels, "col": colors, "pch": symbols[:l],
            "cex": cex_v}


def clPairsLegend(
    x: float,
    y: float,
    class_: Sequence[Any],
    col: Any = None,
    pch: Any = None,
    cex: Any = None,
    box: bool = True,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> dict[str, float]:
    """A legend placed at (x, y) given in the unit square of the plot region.

    ``x`` and ``y`` are converted to user coordinates with the current limits.
    The legend box size depends on R's font metrics, so only the anchor and
    the labels, symbols and colours are logged and drawn.
    """
    if log is None:
        log = PlotLog()
    del cex, box
    if ax is not None:
        usr = (*ax.get_xlim(), *ax.get_ylim())
    else:
        usr = (0.0, 1.0, 0.0, 1.0)
    if tuple(usr) != (0.0, 1.0, 0.0, 1.0):
        x = x * (usr[1] - usr[0]) + usr[0]
        y = y * (usr[3] - usr[2]) + usr[2]
    col_v = 1 if col is None else col
    pch_v = 1 if pch is None else pch
    labels = [_as_char(v) for v in class_]
    log.legend(ax, float(x), float(y), labels, pch_v, col_v)
    return {"x": float(x), "y": float(y)}
