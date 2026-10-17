"""plot.densityMclust: the plot method for a densityMclust fit, drawn from the object's fields.

``what`` is matched with several.ok and the panels are drawn in R's fixed order:
BIC, density, diagnostic. A multivariate fit drops the diagnostic, as R does.

The density panel calls plotDensityMclust1 (d = 1), plotDensityMclust2 (d = 2)
or plotDensityMclustd (d > 2), as R does.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from ._plot_common import extendrange, nclass_sturges, pretty
from .density import dens
from .density_mclust_diagnostic import densityMclust_diagnostic
from .plot_log import PlotLog
from .plot_mclust_bic import plot_mclustBIC
from .plot_mclust import _grid_axes
from .surface_plot import surfacePlot
from .utility_functions import hdrlevels

__all__ = [
    "plot_densityMclust",
    "plotDensityMclust1",
    "plotDensityMclust2",
    "plotDensityMclustd",
]

_WHAT = ("BIC", "density", "diagnostic")


def _field(obj: Any, name: str) -> Any:
    return obj[name] if isinstance(obj, dict) else getattr(obj, name)


def _match(choice: Sequence[str] | str, allowed: Sequence[str]) -> list[str]:
    values = [choice] if isinstance(choice, str) else list(choice)
    bad = [v for v in values if v not in allowed]
    if bad:
        raise ValueError(f"'arg' should be one of {', '.join(map(repr, allowed))}")
    return [name for name in allowed if name in values]


def _parameters(obj: Any) -> dict[str, Any]:
    """The fit's parameters with pro defaulting to 1, as plot.densityMclust sets them."""
    p = dict(_get(obj, "parameters"))
    if p.get("pro") is None:
        p["pro"] = np.array([1.0])
    p["variance"] = dict(p["variance"])
    return p


def _hist_breaks(values: np.ndarray, breaks: Any) -> np.ndarray:
    """hist.default breaks: "Sturges" is pretty(range, nclass.Sturges, min.n = 1)."""
    if isinstance(breaks, str):
        if breaks != "Sturges":
            raise ValueError("breaks must be \"Sturges\", a number, or a vector of breaks")
        return pretty(values, n=nclass_sturges(values), min_n=1)
    arr = np.asarray(breaks, dtype=float).ravel()
    if arr.size == 1:
        return pretty(values, n=int(arr[0]), min_n=1)
    return arr


def plotDensityMclust1(
    x: Any,
    data: Any = None,
    col: Any = "#4D4D4D",
    hist_col: Any = "lightgrey",
    hist_border: Any = "white",
    breaks: Any = "Sturges",
    *,
    ax: Any = None,
    xlim: Sequence[float] | None = None,
    ylim: Sequence[float] | None = None,
    ylab: str = "Density",
    log: PlotLog | None = None,
) -> dict[str, Any]:
    """plot.densityMclust for a one-dimensional fit: the density curve, over a histogram of data when given.

    Returns the evaluated grid and density, the window, and, with data, the histogram.
    The window and the curve are written to ``log`` as R's plot() and lines() would.
    """
    if log is None:
        log = PlotLog()
    obj_data = np.asarray(_get(x, "data"), dtype=float).reshape(-1)
    if xlim is not None:
        xrange = np.asarray([min(xlim), max(xlim)], dtype=float)
    else:
        xrange = extendrange(obj_data, 0.1)
    grid = np.linspace(xrange[0], xrange[1], 1000)
    d = np.asarray(
        dens(grid.reshape(-1, 1), _get(x, "modelName"), _get(x, "parameters"), logarithm=False),
        dtype=float,
    ).reshape(-1)
    if ax is None:
        import matplotlib.pyplot as plt

        ax = plt.gca()
    result: dict[str, Any] = {"x": grid, "density": d}

    if data is None:
        if ylim is not None:
            ylimit = np.asarray([min(ylim), max(ylim)], dtype=float)
        else:
            ylimit = np.asarray([min(0.0, float(d.min())), max(0.0, float(d.max()))])
        # R: plot(eval.points, d, type = "l", xlim, ylim) sets the window, then draws the curve.
        window = log.window(ax, xrange, ylimit)
        log.lines(ax, grid, d, col=col)
        if ax is not None:
            ax.set_ylabel(ylab)
        result.update({"xlim": xrange, "ylim": ylimit, "window": window})
        return result

    observed = np.asarray(data, dtype=float).reshape(-1)
    edges = _hist_breaks(observed, breaks)
    counts, _ = np.histogram(observed, bins=edges, density=True)
    if ax is not None:
        ax.hist(observed, bins=edges, density=True, color=hist_col, edgecolor=hist_border)
    window_x = np.asarray([min(edges.min(), xrange[0]), max(edges.max(), xrange[1])])
    if ylim is not None:
        window_y = np.asarray([min(ylim), max(ylim)], dtype=float)
    else:
        window_y = np.asarray([min(0.0, float(counts.min()), float(d.min())),
                               max(0.0, float(counts.max()), float(d.max()))])
    window = log.window(ax, window_x, window_y)
    log.lines(ax, grid, d, col=col)
    if ax is not None:
        ax.set_ylabel(ylab)
    result.update({"hist_breaks": edges, "hist_density": counts,
                   "xlim": window_x, "ylim": window_y, "window": window})
    return result


def plotDensityMclust2(
    x: Any,
    data: Any = None,
    nlevels: int = 11,
    levels: Sequence[float] | None = None,
    prob: Sequence[float] = (0.25, 0.5, 0.75),
    points_pch: Any = 1,
    points_col: Any = "black",
    points_cex: float = 0.8,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
    **kwargs: Any,
) -> dict[str, np.ndarray]:
    """plot.densityMclust for a two-dimensional fit: surfacePlot of the density, points over it when data is given.

    R's surfacePlot receives the fit's data, or ``data`` when it is given, so the
    grid is taken from the same points that are drawn. ``type = "hdr"`` uses the
    HDR levels of the fit's density, as R does.
    """
    if log is None:
        log = PlotLog()
    points = None if data is None else np.asarray(data, dtype=float)
    surface = np.asarray(_get(x, "data"), dtype=float) if points is None else points
    typ = kwargs.pop("type", "contour")
    if typ == "level":
        typ = "hdr"
    if typ == "hdr":
        density = np.asarray(_get(x, "density"), dtype=float).ravel()
        levels = np.concatenate([np.sort(hdrlevels(density, prob)), [1.1 * float(density.max())]])
        nlevels = len(levels)
    out = surfacePlot(
        surface, _parameters(x), type=typ, nlevels=nlevels, levels=levels,
        prob=prob, ax=ax, log=log, **kwargs,
    )
    if points is not None:
        log.points(ax, points[:, 0], points[:, 1], pch=points_pch, col=points_col)
    return out


def plot_densityMclust(
    x: Any,
    data: Any = None,
    what: Sequence[str] | str = _WHAT,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """Draw the BIC, density and diagnostic panels of a densityMclust fit."""
    if log is None:
        log = PlotLog()
    d = int(np.asarray(_field(x, "d")).ravel()[0])
    panels = _match(what, _WHAT)
    if d > 1:
        panels = [p for p in panels if p != "diagnostic"]

    if "BIC" in panels:
        if ax is not None:
            ax.cla()
        plot_mclustBIC(_field(x, "BIC"), canvas=log, ax=ax)
    if "density" in panels:
        if ax is not None:
            ax.cla()
        if d == 1:
            plotDensityMclust1(x, data=data, ax=ax, log=log)
        elif d == 2:
            plotDensityMclust2(x, data=data, ax=ax, log=log)
        else:
            plotDensityMclustd(x, data=data, ax=ax, log=log)
    if "diagnostic" in panels:
        if ax is not None:
            ax.cla()
        densityMclust_diagnostic(x, ax=ax, log=log)
    return None


def _get(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _span(values: Any) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float).ravel()
    return float(np.min(arr)), float(np.max(arr))


def _axis_sides(log: PlotLog, i: int, j: int, nc: int) -> None:
    """The axis() calls plotDensityMclustd makes for panel (i, j), 1-based, in R's order."""
    if i == 1 and j % 2 == 0:
        log.log.append(("V", [["axis"], [i, j, 3]]))
    if i == nc and j % 2 == 1:
        log.log.append(("V", [["axis"], [i, j, 1]]))
    if j == 1 and i % 2 == 0:
        log.log.append(("V", [["axis"], [i, j, 2]]))
    if j == nc and i % 2 == 1:
        log.log.append(("V", [["axis"], [i, j, 4]]))


def plotDensityMclustd(
    x: Any,
    data: Any = None,
    nlevels: int = 11,
    levels: Any = None,
    prob: Sequence[float] = (0.25, 0.5, 0.75),
    points_pch: Any = 1,
    points_col: Any = "black",
    points_cex: float = 0.8,
    gap: float = 0.2,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """plot.densityMclust for a fit with d > 2: a d by d grid of pairwise density panels.

    The diagonal panels hold the variable name, with the window of ``data`` (or of the
    fit's data). Each off-diagonal panel is ``surfacePlot`` of the pair of variables,
    with the density contours of the fit. ``data``, when given, is drawn as points in
    the upper triangle. ``points_col`` is the palette name; R's default ``1`` is black.
    The layout (mfrow, mar, oma) and the axis sides follow plotDensityMclustd.
    """
    if log is None:
        log = PlotLog()
    del points_cex
    obj = np.asarray(_get(x, "data"), dtype=float)
    nc = int(obj.shape[1])
    pts = None if data is None else np.asarray(data, dtype=float)
    draw = obj if pts is None else pts
    names = _get(x, "colnames")
    names = [str(s) for s in names] if names is not None else [""] * nc

    params = _get(x, "parameters")
    pro = np.asarray(_get(params, "pro"), dtype=float).ravel()
    mean = np.asarray(_get(params, "mean"), dtype=float).reshape(nc, -1)
    sigma = np.asarray(_get(_get(params, "variance"), "sigma"), dtype=float).reshape(nc, nc, -1)

    log.log.append(("V", [["layout"], [nc, nc], [gap / 2.0] * 4, [3.0] * 4]))
    grid = _grid_axes(ax, nc)
    for i in range(nc):
        for j in range(nc):
            log.panel = (i + 1, j + 1)
            sub = grid[i][j]
            if i == j:
                lo, hi = _span(draw[:, i])
                usr = log.window(sub, (lo, hi), (lo, hi), xaxs="r", yaxs="r")
                xm = (usr[0] + usr[1]) / 2.0
                ym = (usr[2] + usr[3]) / 2.0
                log.log.append(("T", [[xm], [ym], [names[i]]]))
                if sub is not None:
                    sub.text(xm, ym, names[i], ha="center", va="center", fontsize=12)
                    sub.set_xticks([])
                    sub.set_yticks([])
            else:
                idx = [j, i]
                sub_par = {
                    "pro": pro,
                    "mean": mean[idx, :],
                    "variance": {"sigma": sigma[np.ix_(idx, idx)]},
                }
                log.window(sub, _span(obj[:, j]), _span(obj[:, i]))
                surfacePlot(obj[:, idx], sub_par, nlevels=nlevels, levels=levels,
                            prob=prob, ax=sub, log=log)
                if sub is not None:
                    sub.set_xticks([])
                    sub.set_yticks([])
                if pts is not None and j > i:
                    log.points(sub, pts[:, j], pts[:, i], pch=points_pch, col=points_col)
            _axis_sides(log, i + 1, j + 1, nc)
    log.panel = (1, 1)
    return None
