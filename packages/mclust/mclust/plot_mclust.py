"""plot.Mclust: the plot method for an Mclust fit, drawn from the object's fields.

The panels come from the translated helpers, in R's fixed order: BIC, classification,
uncertainty, density. Each takes the object's fields only, so the plot does not
depend on the fitting code.

Not translated here: the density panel for d = 1 (plotDensityMclust1, owner
d7f9caf5-4ae4-4346-b3ba-df333a9da393) and every panel for d > 2 (the coordProj pairs grid).
Those raise NotImplementedError.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .coord_proj import coordProj
from .mclust_1d_plot import mclust1Dplot
from .mclust_2d_plot import mclust2Dplot
from .plot_log import PlotLog
from .plot_mclust_bic import plot_mclustBIC
from .surface_plot import surfacePlot

__all__ = ["plot_Mclust"]

_WHAT = ("BIC", "classification", "uncertainty", "density")


def _field(obj: Any, name: str) -> Any:
    return obj[name] if isinstance(obj, dict) else getattr(obj, name)


def _match(choice: Sequence[str] | str, allowed: Sequence[str]) -> list[str]:
    values = [choice] if isinstance(choice, str) else list(choice)
    bad = [v for v in values if v not in allowed]
    if bad:
        raise ValueError(f"'arg' should be one of {', '.join(map(repr, allowed))}")
    return [name for name in allowed if name in values]


def _colnames(x: Any, d: int) -> list[str]:
    names = _field(x, "colnames") if isinstance(x, dict) else None
    if names is None or len(np.atleast_1d(names)) != d:
        return [str(k + 1) for k in range(d)]
    return [str(v) for v in np.atleast_1d(names)]


def _subset(pars: dict[str, Any], dims: list[int]) -> dict[str, Any]:
    """The parameters restricted to the chosen dimensions, as plot.Mclust does for d > 1."""
    mean = np.asarray(pars["mean"], dtype=float)[dims, :]
    sigma = np.asarray(pars["variance"]["sigma"], dtype=float)
    sigma = sigma[np.ix_(dims, dims, np.arange(sigma.shape[2]))]
    return {"pro": pars["pro"], "mean": mean,
            "variance": {"d": len(dims), "sigma": sigma}}


def _grid_axes(ax: Any, d: int) -> list[list[Any]]:
    """A d by d grid of axes in the area of ``ax``, which is replaced. None when not drawing."""
    if ax is None:
        return [[None] * d for _ in range(d)]
    fig = ax.figure
    x0, y0, w, h = ax.get_position().bounds
    ax.remove()
    cw, ch = w / d, h / d
    grid = [[None] * d for _ in range(d)]
    for i in range(d):
        for j in range(d):
            grid[i][j] = fig.add_axes([x0 + j * cw, y0 + (d - 1 - i) * ch, cw, ch])
    return grid


def _pairs_grid(data: np.ndarray, dims: list[int], names: list[str], ax: Any,
                log: PlotLog, panel_fn: Any) -> None:
    """plot.Mclust's d > 2 layout: the diagonal labels, and a coordProj panel for each pair.

    Each panel's usr box is logged with its (row, column), as par("mfg") reports it.
    """
    d = len(dims)
    grid = _grid_axes(ax, d)
    for i in range(d):
        for j in range(d):
            log.panel = (i + 1, j + 1)
            sub = grid[i][j]
            if i == j:
                x = data[:, dims[j]]
                y = data[:, dims[i]]
                log.window(sub, (float(x.min()), float(x.max())),
                           (float(y.min()), float(y.max())), xaxs="r", yaxs="r")
                if sub is not None:
                    sub.text(0.5, 0.5, names[i], transform=sub.transAxes,
                             ha="center", va="center", fontsize=12)
                    sub.set_xticks([])
                    sub.set_yticks([])
            else:
                panel_fn(sub, [dims[j] + 1, dims[i] + 1])
                if sub is not None:
                    sub.set_xticks([])
                    sub.set_yticks([])
    log.panel = (1, 1)


def plot_Mclust(
    x: Any,
    what: Sequence[str] | str = _WHAT,
    dimens: Sequence[int] | None = None,
    xlab: str | None = None,
    ylab: str | None = None,
    addEllipses: bool = True,
    main: Any = False,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """Draw the BIC, classification, uncertainty and density panels of an Mclust fit.

    ``x`` holds the fields of the R object: ``data``, ``classification``, ``z``,
    ``parameters``, ``BIC``, ``d`` and ``G``. ``dimens`` takes 1-based dimensions.
    """
    del xlab, ylab, main
    if log is None:
        log = PlotLog()
    data = np.asarray(_field(x, "data"), dtype=float)
    if data.ndim == 1:
        data = data[:, None]
    d_all = data.shape[1]
    dims = list(range(d_all)) if dimens is None else [int(i) - 1 for i in dimens if int(i) <= d_all]
    d = len(dims)
    panels = _match(what, _WHAT)
    cls = _field(x, "classification")
    z = _field(x, "z")
    pars = _field(x, "parameters")

    if "BIC" in panels:
        if ax is not None:
            ax.cla()
        plot_mclustBIC(_field(x, "BIC"), canvas=log, ax=ax)

    names = [str(v) for v in _colnames(x, d_all)]
    if "classification" in panels:
        if ax is not None:
            ax.cla()
        if d == 1:
            mclust1Dplot(data[:, dims], classification=cls, z=z,
                         what="classification", ax=ax, log=log)
        elif d == 2:
            mclust2Dplot(data[:, dims],
                         parameters=_subset(pars, dims) if addEllipses else None,
                         classification=cls, what="classification", ax=ax, log=log)
        else:
            def panel(sub, dimens2, _pars=pars):
                coordProj(data, dimens=dimens2, parameters=_pars, classification=cls,
                          what="classification", addEllipses=addEllipses, ax=sub, log=log)
            _pairs_grid(data, dims, [names[k] for k in dims], ax, log, panel)

    if "uncertainty" in panels:
        if ax is not None:
            ax.cla()
        if d == 1:
            mclust1Dplot(data[:, dims], parameters=pars, z=z,
                         what="uncertainty", ax=ax, log=log)
        elif d == 2:
            mclust2Dplot(data[:, dims], parameters=_subset(pars, dims), z=z,
                         classification=cls, what="uncertainty",
                         addEllipses=addEllipses, ax=ax, log=log)
        else:
            def panel(sub, dimens2, _pars=pars):
                coordProj(data, dimens=dimens2, parameters=_pars, z=z, classification=cls,
                          what="uncertainty", addEllipses=addEllipses, ax=sub, log=log)
            _pairs_grid(data, dims, [names[k] for k in dims], ax, log, panel)

    if "density" in panels:
        if ax is not None:
            ax.cla()
        # plot.Mclust.density: as.densityMclust(object) for d = 1, the object's own
        # surface for d = 2, and plotDensityMclustd on the chosen dimensions for d > 2.
        # The helpers are imported here: plot_density_mclust imports this module.
        from .plot_density_mclust import plotDensityMclust1, plotDensityMclustd

        if d == 1:
            plotDensityMclust1(x, ax=ax, log=log)
        elif d == 2:
            surfacePlot(data, pars, what="density", ax=ax, log=log)
        else:
            sub = {
                "data": data[:, dims],
                "colnames": [_colnames(x, d_all)[k] for k in dims],
                "parameters": _subset_density_parameters(pars, dims, d_all),
            }
            plotDensityMclustd(sub, ax=ax, log=log)
    return None


def _subset_density_parameters(pars: Any, dims: list[int], d_all: int) -> dict[str, Any]:
    """The parameters with the mean and the covariance cut to ``dims``, as plot.Mclust sets them."""
    pro = np.asarray(_field(pars, "pro"), dtype=float).ravel()
    mean = np.asarray(_field(pars, "mean"), dtype=float).reshape(d_all, -1)[dims, :]
    sigma = np.asarray(_field(_field(pars, "variance"), "sigma"), dtype=float)
    sigma = sigma.reshape(d_all, d_all, -1)[np.ix_(dims, dims, range(sigma.reshape(d_all, d_all, -1).shape[2]))]
    return {"pro": pro, "mean": mean, "variance": {"sigma": sigma}}
