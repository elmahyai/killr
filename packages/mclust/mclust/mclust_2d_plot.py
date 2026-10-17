"""mclust2Dplot: two-dimensional classification, error, uncertainty and point plots.

``coordProj`` (coord_proj.py) uses the same drawing code with a projection of
the data and the parameters onto two chosen dimensions.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .class_error import classError
from .map_util import map as r_map
from .mclust_options import mclust_options
from .mvn2plot import mvn2plot
from .plot_log import (SQRT_EPS, PlotLog, _as_char, adjustcolor, bubble, class_levels,
                       symb2fill, symb2open)

__all__ = ["mclust2Dplot", "draw_2d", "class_symbols_colors"]

_WHAT_2D = ("classification", "uncertainty", "error")


def class_symbols_colors(levels: Sequence[str], symbols: Any, colors: Any) -> tuple[list, list]:
    """The symbol and colour defaults mclust2Dplot and coordProj use for L classes."""
    L = len(levels)
    noise = len(levels) > 0 and levels[0] == "0"
    opt_sym = list(mclust_options("classPlotSymbols"))
    opt_col = list(mclust_options("classPlotColors"))
    if symbols is None:
        if L <= len(opt_sym):
            symbols = opt_sym[:L]
            if noise:
                symbols = ([16] + symbols)[:L]
        elif L <= 9:
            symbols = [str(i) for i in range(1, 10)]
        elif L <= 26:
            symbols = [chr(ord("A") + i) for i in range(26)]
    elif len(symbols) == 1:
        symbols = [symbols[0]] * L
    if colors is None:
        if L <= len(opt_col):
            colors = opt_col[:L]
            if noise:
                colors = list(dict.fromkeys(["black"] + colors))[:L]
    elif len(colors) == 1:
        colors = [colors[0]] * L
    symbols = list(symbols)
    colors = list(colors)
    if len(symbols) < L:
        symbols = [16] * L
    if len(colors) < L:
        colors = ["black"] * L
    return symbols, colors


def _parameters_2d(parameters: dict | None, dim_sel: Sequence[int] | None, d_expected: int = 2):
    """(mu, sigma, haveParams) with mu of shape (2, G) and sigma of shape (2, 2, G)."""
    if parameters is None:
        return None, None, False
    mu = np.asarray(parameters["mean"], dtype=float)
    if mu.ndim == 1:
        mu = mu.reshape(-1, 1)
    sigma = np.asarray(parameters["variance"]["sigma"], dtype=float)
    if dim_sel is not None:
        idx = np.asarray(dim_sel, dtype=int) - 1
        mu = mu[idx, :]
        sigma = sigma[np.ix_(idx, idx, np.arange(sigma.shape[2]))]
    if sigma.ndim != 3:
        return mu, sigma, False
    if mu.shape[1] != sigma.shape[2]:
        return mu, sigma, False
    return mu, sigma, True


def draw_2d(
    X: np.ndarray,
    mu: Any,
    sigma: Any,
    have_params: bool,
    classification: Any,
    truth: Any,
    uncertainty: Any,
    what: str,
    add_ellipses: bool,
    fillEllipses: bool,
    symbols: Any,
    colors: Any,
    xlim: Any,
    ylim: Any,
    cex: float,
    PCH: Any,
    coord: bool,
    ax: Any,
    log: PlotLog,
) -> None:
    """The drawing shared by mclust2Dplot (coord False) and coordProj (coord True).

    ``X`` is the two-column data already projected. ``coord`` selects the
    error branch of coordProj, which uses the open and filled symbols of the
    whole symbol list and the sorted levels of the truth.
    """
    fill = fillEllipses
    cls_chr = None
    U: list[str] = []
    L = None
    if classification is not None:
        cls_chr, U = class_levels(classification)
        L = len(U)
        symbols, colors = class_symbols_colors(U, symbols, colors)

    truth_chr = None
    if truth is not None:
        truth_chr = [_as_char(v) for v in truth]

    bad = what == "classification" and classification is None
    bad = bad or (what == "uncertainty" and uncertainty is None)
    bad = bad or (what == "error" and (classification is None or truth_chr is None))
    if bad:
        if not coord:
            raise ValueError("insufficient input for specified plot")
        what = "bad"

    if what == "classification":
        log.window(ax, xlim, ylim)
        for k in range(L):
            I = cls_chr == U[k]
            log.points(ax, X[I, 0], X[I, 1], symbols[k], colors[k])
    elif what == "error":
        errors = np.asarray(
            classError(cls_chr.tolist(), truth_chr)["misclassified"], dtype=float)
        log.window(ax, xlim, ylim)
        good = np.ones(X.shape[0], dtype=bool)
        good[errors.astype(int) - 1] = False
        if coord:
            CLASSES = sorted(set(truth_chr))
            opts = list(mclust_options("classPlotSymbols"))
            sym_open = symb2open(opts)
            sym_fill = symb2fill(opts)
            if L > len(sym_open):
                log.points(ax, X[good, 0], X[good, 1], 1, colors)
                log.points(ax, X[~good, 0], X[~good, 1], 16)
            else:
                for k in range(L):
                    K = np.array([t == CLASSES[k] for t in truth_chr])
                    I = K & good
                    if I.any():
                        log.points(ax, X[I, 0], X[I, 1], sym_open[k], colors[k])
                    I = K & ~good
                    if I.any():
                        log.points(ax, X[I, 0], X[I, 1], sym_fill[k], "black")
        else:
            CLASSES = list(dict.fromkeys(truth_chr))
            sym_open = [2, 0, 1, 5]
            sym_fill = [17, 15, 16, 18]
            if L > 4:
                log.points(ax, X[good, 0], X[good, 1], 1, colors)
                log.points(ax, X[~good, 0], X[~good, 1], 16)
            else:
                for k in range(L):
                    K = np.array([t == CLASSES[k] for t in truth_chr])
                    log.points(ax, X[K, 0], X[K, 1], sym_open[k], colors[k])
                    I = K & ~good
                    if I.any():
                        log.points(ax, X[I, 0], X[I, 1], sym_fill[k], "black")
    elif what == "uncertainty":
        unc = np.asarray(uncertainty, dtype=float)
        u = (unc - unc.min()) / (unc.max() - unc.min() + SQRT_EPS)
        b = bubble(u, cex=(cex * 0.3, cex * 2.0), alpha=(0.3, 0.9))
        cl = np.array([U.index(c) for c in cls_chr], dtype=int)
        cols = [adjustcolor(colors[c], float(a)) for c, a in zip(cl, b["alpha"])]
        log.window(ax, xlim, ylim)
        log.points(ax, X[:, 0], X[:, 1], 19, cols)
        fill = False
    else:
        log.window(ax, xlim, ylim)
        log.points(ax, X[:, 0], X[:, 1], PCH, "black")

    if have_params and add_ellipses:
        G = mu.shape[1]
        for g in range(G):
            col = colors[g] if fill else ["grey30"] * 3
            mvn2plot(mu[:, g], sigma[:, :, g], k=15, fillEllipse=fill, col=col,
                     ax=ax, log=log)


def mclust2Dplot(
    data: Any,
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
    xlim: Sequence[float] | None = None,
    ylim: Sequence[float] | None = None,
    scale: bool = False,
    cex: float = 1.0,
    PCH: Any = ".",
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """Plot two-dimensional data with the classes, uncertainty or errors and the ellipses.

    ``parameters`` is a plain dict: ``mean`` (2 by G) and ``variance`` =
    {``sigma``: 2 by 2 by G}. The fitted-model object is not used.
    """
    if log is None:
        log = PlotLog()
    X = np.asarray(data, dtype=float)
    if X.ndim != 2 or X.shape[1] != 2:
        raise ValueError("data must be two dimensional")
    if fillEllipses is None:
        fillEllipses = bool(mclust_options("fillEllipses"))
    if classification is None and z is not None:
        classification = r_map(np.asarray(z, dtype=float), warn=False)
    if uncertainty is None and z is not None:
        uncertainty = 1.0 - np.asarray(z, dtype=float).max(axis=1)
    mu, sigma, have_params = _parameters_2d(parameters, None)
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
        else:
            if len({str(v) for v in truth}) != len({str(v) for v in classification}):
                truth = None
    if what not in _WHAT_2D:
        raise ValueError(f"what must be one of {_WHAT_2D}")
    draw_2d(X, mu, sigma, have_params, classification, truth, uncertainty, what,
            addEllipses, fillEllipses, symbols, colors, xlim, ylim, cex, PCH,
            coord=False, ax=ax, log=log)

