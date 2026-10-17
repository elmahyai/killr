"""mclust1Dplot: one-dimensional classification, error, uncertainty and density plots."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .class_error import classError
from .density import dens
from .map_util import map as r_map
from .mclust_options import mclust_options
from .plot_log import PlotLog, adjustcolor, bubble, class_levels, grid1, SQRT_EPS, extendrange

__all__ = ["mclust1Dplot"]

_WHAT = ("classification", "density", "error", "uncertainty")


def mclust1Dplot(
    data: Any,
    parameters: dict | None = None,
    z: Any = None,
    classification: Sequence[Any] | None = None,
    truth: Sequence[Any] | None = None,
    uncertainty: Sequence[float] | None = None,
    what: str = "classification",
    symbols: Sequence[Any] | None = None,
    colors: Sequence[str] | None = None,
    ngrid: int | None = None,
    xlim: Sequence[float] | None = None,
    ylim: Sequence[float] | None = None,
    cex: float = 1.0,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """Plot one-dimensional data as mclust's R function does.

    ``parameters`` is a plain dict with ``mean`` (1 by G), ``pro`` and
    ``variance`` = {``sigmasq``, ``G``}; no fitted model object is used.
    """
    if log is None:
        log = PlotLog()
    arr = np.asarray(data, dtype=float)
    if arr.ndim == 2:
        if arr.shape[1] != 1:
            raise ValueError("for one-dimensional data only")
        arr = arr[:, 0]
    data = arr.ravel()
    n = data.size
    if ngrid is None:
        ngrid = n
    zz = None if z is None else np.asarray(z, dtype=float)
    if classification is None and zz is not None:
        classification = r_map(zz, warn=False)
    if uncertainty is None and zz is not None:
        uncertainty = 1.0 - zz.max(axis=1)

    have_params = parameters is not None
    G_params = None
    if have_params:
        mu = np.atleast_2d(np.asarray(parameters["mean"], dtype=float))
        G_params = mu.shape[1]

    xlim_v = (float(data.min()), float(data.max())) if xlim is None else tuple(xlim)

    if truth is not None:
        if classification is None:
            classification = truth
            truth = None
        else:
            if len({str(v) for v in truth}) != len({str(v) for v in classification}):
                truth = None
            else:
                truth = [str(v) for v in truth]

    cls_chr = None
    U: list[str] = []
    L = G_params
    if classification is not None:
        cls_chr, U = class_levels(classification)
        L = len(U)
        if symbols is None:
            symbols = ["|"] * L
        elif len(symbols) == 1:
            symbols = [symbols[0]] * L
        elif len(symbols) < L:
            symbols = ["|"] * L
        if colors is None:
            colors = list(mclust_options("classPlotColors"))[:L]
        elif len(colors) == 1:
            colors = [colors[0]] * L
        elif len(colors) < L:
            colors = ["black"] * L

    if what not in _WHAT:
        raise ValueError(f"what must be one of {_WHAT}")
    bad = what == "classification" and classification is None
    bad = bad or (what == "uncertainty" and uncertainty is None)
    bad = bad or (what == "error" and (classification is None or truth is None))
    if bad:
        raise ValueError("insufficient input for specified plot")

    M = L
    if what == "classification":
        ylim_v = tuple(extendrange([0, M], 0.1)) if ylim is None else tuple(ylim)
        log.window(ax, xlim_v, ylim_v)
        for k in range(L):
            sel = cls_chr == U[k]
            pts = data[sel]
            cnt = pts.size
            if symbols[k] == "|":
                log.points(ax, pts, np.zeros(cnt), "|", "black")
                log.points(ax, pts, np.full(cnt, float(k + 1)), "|", colors[k])
            else:
                log.points(ax, pts, np.zeros(cnt), symbols[k], "black")
                log.points(ax, pts, np.full(cnt, float(k + 1)), symbols[k], colors[k])
    elif what == "error":
        errors = np.asarray(classError(cls_chr.tolist(), list(truth))["misclassified"], dtype=float)
        ylim_v = tuple(extendrange([0, M], 0.1)) if ylim is None else tuple(ylim)
        log.window(ax, xlim_v, ylim_v)
        good = np.ones(n, dtype=bool)
        good[errors.astype(int) - 1] = False
        for k in range(L):
            K = cls_chr == U[k]
            I = K & good
            if I.any():
                l = int(I.sum())
                log.points(ax, data[I], np.zeros(l), "|", colors[k])
            I = K & ~good
            if I.any():
                l = int(I.sum())
                log.points(ax, data[I], np.full(l, float(k + 1)), "|", colors[k])
    elif what == "uncertainty":
        unc = np.asarray(uncertainty, dtype=float)
        u = (unc - unc.min()) / (unc.max() - unc.min() + SQRT_EPS)
        b = bubble(u, cex=(cex * 0.3, cex * 2.0), alpha=(0.3, 1.0))
        if cls_chr is None:
            cls_idx = np.zeros(n, dtype=int)
            cols_all = ["black"] if colors is None else list(colors)
        else:
            cls_idx = np.array([U.index(c) for c in cls_chr], dtype=int)
            cols_all = list(colors)
        ylim_v = (0.0, 1.0) if ylim is None else tuple(ylim)
        log.window(ax, xlim_v, ylim_v)
        for i in range(n):
            col_i = adjustcolor(cols_all[cls_idx[i]], float(b["alpha"][i]))
            log.lines(ax, [data[i], data[i]], [0.0, unc[i]], col=col_i)
    elif what == "density":
        if (parameters.get("pro") is None) and G_params != 1:
            raise ValueError("mixing proportions missing")
        x = grid1(ngrid, xlim_v, edge=True)
        y = np.asarray(dens(x, "V", parameters), dtype=float)
        log.window_xy(ax, x, y, xlim=xlim_v, ylim=None)
        log.lines(ax, x, y)
