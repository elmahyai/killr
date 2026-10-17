"""Translation of ``plot.mclustBIC`` (mclust 6.1.3) for one-component objects.

``plot.mclustBIC`` draws the BIC values of each model against the number of
components: one ``matplot`` call with ``type = "b"``, a legend, and the x axis
ticks at the component counts. The object is the matrix that ``mclustBIC``
returns, with one row per G and one column per model.

Scope: this translation is checked on G = 1 objects only. The multi-component
path of ``mclustBIC`` is verified separately.

The symbols, colours and model columns are chosen as R chooses them. The
values are not changed. Matplotlib draws the points and the legend.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Sequence

import numpy as np

from ._plot_common import Canvas, _marker
from .mclust_options import mclust_options

__all__ = ["plot_mclustBIC"]


def _get(x: Any, name: str, default: Any = None) -> Any:
    if isinstance(x, Mapping):
        return x.get(name, default)
    return getattr(x, name, default)


def plot_data(x: Any, G: Sequence[float] | None = None,
              modelNames: Sequence[str] | None = None,
              symbols: dict[str, Any] | None = None,
              colors: dict[str, str] | None = None) -> dict[str, Any]:
    """The data part of ``plot.mclustBIC``: the model columns, symbols, colours, y range and x values.

    Nothing is drawn here. The timed call in the proof is this function.
    """
    values = np.atleast_2d(np.asarray(_get(x, "values", x), dtype=float))
    n_rows, n_cols = values.shape
    rows = _get(x, "G")
    rows = np.arange(1, n_rows + 1, dtype=float) if rows is None else np.asarray(rows, dtype=float)
    cols = _get(x, "modelNames")
    cols = [str(i + 1) for i in range(n_cols)] if cols is None else [str(c) for c in cols]
    if modelNames is None:
        modelNames = cols
    modelNames = [str(m) for m in modelNames]
    G_arg = rows if G is None else np.asarray(G, dtype=float)

    if symbols is None:
        opt_sym = mclust_options("bicPlotSymbols")
        symbols = {m: opt_sym[m] for m in modelNames}
    if colors is None:
        opt_col = mclust_options("bicPlotColors")
        colors = {m: opt_col[m] for m in modelNames}

    idx = [cols.index(m) for m in modelNames]
    sub = values[:, idx]
    finite = sub[~np.isnan(sub)]
    ylim = (float(finite.min()), float(finite.max()))
    return {
        "x": rows,
        "y": sub,
        "xlim": (float(np.min(G_arg)), float(np.max(G_arg))),
        "ylim": ylim,
        "modelNames": modelNames,
        "symbols": symbols,
        "colors": colors,
        "pch": [symbols[m] for m in modelNames],
        "col": [colors[m] for m in modelNames],
    }


def plot_mclustBIC(x: Any, G: Sequence[float] | None = None,
                   modelNames: Sequence[str] | None = None,
                   symbols: dict[str, Any] | None = None,
                   colors: dict[str, str] | None = None,
                   xlab: str | None = None, ylab: str = "BIC",
                   legend: bool = True, ax: Any = None,
                   canvas: Canvas | None = None) -> tuple[dict[str, Any], Canvas]:
    """Plot the BIC values of each model against the number of components.

    ``x`` is an ``mclustBIC`` result (a mapping with ``values``, ``G`` and
    ``modelNames``) or a matrix with the same layout. Returns the symbols used
    for each model, as R returns them invisibly, and the canvas with the log.
    """
    canvas = canvas or Canvas()
    if xlab is None:
        xlab = "Number of components"
    d = plot_data(x, G=G, modelNames=modelNames, symbols=symbols, colors=colors)

    canvas.matplot(ax, d["x"], d["y"], d["pch"], d["col"], xlim=d["xlim"], ylim=d["ylim"])
    canvas.value("axis1", d["x"])

    if ax is not None:
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        if legend:
            _draw_legend(ax, d["modelNames"], d["pch"], d["col"])
    return d["symbols"], canvas


def _draw_legend(ax: Any, labels: Sequence[str], pch: Sequence[Any], col: Sequence[Any]) -> None:
    """The key glyphs of ``legend(x = "bottomright", ncol = 2)``. Not logged, as in R's trace."""
    from matplotlib.lines import Line2D

    handles = [Line2D([], [], marker=_marker(p), linestyle="none", color=str(c))
               for p, c in zip(pch, col)]
    ax.legend(handles, list(labels), loc="lower right", ncol=2, frameon=True)
