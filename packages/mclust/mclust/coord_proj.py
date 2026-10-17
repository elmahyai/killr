"""coordProj: coordinate projection of two chosen dimensions (mclust graphics.R)."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .map_util import map as r_map
from .mclust_2d_plot import _parameters_2d, draw_2d
from .mclust_options import mclust_options
from .plot_log import PlotLog, _as_char

__all__ = ["coordProj"]

_CHOICES = ("classification", "error", "uncertainty")


def _match_what(what: str) -> str:
    """R's charmatch: an exact or unique partial match, else 'bad'."""
    if what in _CHOICES:
        return what
    hits = [c for c in _CHOICES if c.startswith(what)]
    return hits[0] if len(hits) == 1 and what else "bad"


def coordProj(
    data: Any,
    dimens: Sequence[int] = (1, 2),
    parameters: dict | None = None,
    z: Any = None,
    classification: Sequence[Any] | None = None,
    truth: Sequence[Any] | None = None,
    uncertainty: Sequence[float] | None = None,
    what: str = "classification",
    addEllipses: bool = True,
    fillEllipses: bool | None = None,
    symbols: Sequence[Any] | None = None,
    colors: Sequence[str] | None = None,
    scale: bool = False,
    xlim: Sequence[float] | None = None,
    ylim: Sequence[float] | None = None,
    cex: float = 1.0,
    PCH: Any = ".",
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """Plot two chosen coordinates of the data, with the projected ellipses.

    ``parameters`` is a plain dict: ``mean`` (p by G) and ``variance`` =
    {``sigma``: p by p by G}, the same numeric inputs as mclust2Dplot.
    """
    if log is None:
        log = PlotLog()
    dims = tuple(int(d) for d in dimens) if dimens is not None else (1, 2)
    if fillEllipses is None:
        fillEllipses = bool(mclust_options("fillEllipses"))
    if classification is None and z is not None:
        classification = r_map(np.asarray(z, dtype=float), warn=False)
    if uncertainty is None and z is not None:
        uncertainty = 1.0 - np.asarray(z, dtype=float).max(axis=1)
    full = np.asarray(data, dtype=float)
    X = full[:, [d - 1 for d in dims]]
    if X.shape[1] != 2:
        raise ValueError("need two dimensions")
    mu, sigma, have_params = _parameters_2d(parameters, dims)
    if xlim is None:
        xlim = (float(X[:, 0].min()), float(X[:, 0].max()))
    if ylim is None:
        ylim = (float(X[:, 1].min()), float(X[:, 1].max()))
    if scale:
        d = (xlim[1] - xlim[0]) - (ylim[1] - ylim[0])
        if d > 0:
            ylim = (ylim[0] - d / 2, ylim[1] + d / 2)
        else:
            xlim = (xlim[0] + d / 2, xlim[1] - d / 2)
    if truth is not None:
        if classification is None:
            classification = truth
            truth = None
    if classification is not None:
        classification = [_as_char(v) for v in classification]
    what_k = _match_what(str(what if isinstance(what, str) else what[0]))
    draw_2d(X, mu, sigma, have_params, classification, truth, uncertainty, what_k,
            addEllipses, fillEllipses, symbols, colors, xlim, ylim, cex, PCH,
            coord=True, ax=ax, log=log)
