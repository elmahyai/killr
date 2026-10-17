"""Translation of ``plot.MclustDR`` and ``plotEvalues.MclustDR`` (mclust 6.1.3).

Each function draws the same primitives R draws, in the same order, through a
``Canvas``. The returned canvas holds the log: window limits, points, lines,
image and contour grids, and the values R returns. ``fig`` is optional. When
it is given, the Matplotlib figure shows the same data. The proof compares the
log, not the pixels.

The R graphics helpers used here (``clPairs`` and ``surfacePlot``) are not
translated here. Their drawing is written inline so that this module does not
depend on the helpers being translated.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

from mclust._plot_common import (
    R_COLOR_HEX,
    Canvas,
    adjustcolor_hex,
    boxplot_stats,
    gray_colors,
    pairs_panels,
    pretty,
    _range,
)
from mclust.dr_predict import predict2D_MclustDR
from mclust.mclust_options import mclust_options
from mclust.projpar_mclust_dr import projpar_MclustDR

__all__ = ["plot_MclustDR", "plotEvalues_MclustDR"]

_DEFAULT_WHAT = ("scatterplot", "pairs", "contour", "classification",
                 "boundaries", "density", "evalues")
_LETTERS = [chr(ord("A") + i) for i in range(26)]


def _get(obj: Any, key: str) -> Any:
    return obj[key]


def _axes(fig: Any) -> Any:
    return None if fig is None else fig.add_subplot(111)


def _grid1(n: int, lo: float, hi: float) -> np.ndarray:
    """``grid1(n, range, edge = TRUE)``."""
    return np.linspace(min(lo, hi), max(lo, hi), n)


def _mixture_density(gx: np.ndarray, gy: np.ndarray, pro: np.ndarray,
                     means: np.ndarray, sigmas: np.ndarray) -> np.ndarray:
    """Density of a bivariate Gaussian mixture on the grid ``gx`` x ``gy``.

    ``means`` is G x 2 and ``sigmas`` is 2 x 2 x G. Returns the matrix with
    ``gx`` down the rows and ``gy`` across the columns, as ``surfacePlot`` does.
    """
    xx, yy = np.meshgrid(gx, gy, indexing="ij")
    pts = np.column_stack([xx.ravel(), yy.ravel()])
    total = np.zeros(pts.shape[0])
    for j in range(means.shape[0]):
        cov = sigmas[:, :, j]
        inv = np.linalg.inv(cov)
        diff = pts - means[j]
        quad = np.einsum("ij,jk,ik->i", diff, inv, diff)
        logdet = math.log(np.linalg.det(cov))
        logd = -0.5 * (2.0 * math.log(2.0 * math.pi) + logdet + quad)
        total += pro[j] * np.exp(logd)
    return total.reshape(gx.size, gy.size)


def _dnorm(x: np.ndarray, mu: float, sd: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - mu) / sd) ** 2) / (sd * math.sqrt(2.0 * math.pi))


def plotEvalues_MclustDR(x: Any, numdir: int | None = None, plot: bool = False,
                         legend: bool = True, ylim: Sequence[float] | None = None,
                         fig: Any = None, canvas: Canvas | None = None,
                         record_values: bool = True) -> Canvas:
    """Eigenvalues of the MclustDR directions, with the mean and variance contributions.

    Logs ``dim``, ``evalues``, ``mean.contrib`` and ``var.contrib``. When
    ``plot`` is true it also draws the line plot and logs its window.
    """
    canvas = canvas or Canvas()
    G = int(_get(x, "G"))
    f = np.asarray(_get(x, "pro"), dtype=float)
    lam = float(_get(x, "lambda"))
    if numdir is None:
        numdir = int(_get(x, "numdir"))
    dim = np.arange(1, int(numdir) + 1)
    d = dim.size
    par = projpar_MclustDR(x, dim, center=True, raw=True)
    mu = np.asarray(par["mean"], dtype=float)
    sigma_g = np.asarray(par["variance"], dtype=float)

    m1 = mu.T @ np.diag(f) @ mu
    l1 = 2.0 * lam * np.diag(m1.T @ m1)

    s = np.zeros((d, d))
    for j in range(G):
        s = s + f[j] * sigma_g[:, :, j]
    m2 = np.zeros((d, d))
    for j in range(G):
        c = sigma_g[:, :, j] - s
        m2 = m2 + f[j] * (c @ c.T)
    l2 = 2.0 * (1.0 - lam) * np.diag(m2)

    evalues = np.asarray(_get(x, "evalues"), dtype=float)[dim - 1]

    if plot:
        ax = _axes(fig)
        if ylim is None:
            top = float(np.max(evalues)) + (float(np.max(evalues) - np.min(evalues))) * 0.05
            ylim = (min(0.0, top), max(0.0, top))
        canvas.window(ax, _range(dim), ylim)
        canvas.xy(ax, dim, evalues, type="b", pch=16, col="black")
        canvas.xy(ax, dim, l1, type="b", pch=22, col="black")
        canvas.xy(ax, dim, l2, type="b", pch=2, col="black")
        if ax is not None and legend:
            ax.legend(["Eigenvalues", "from means", "from vars"], loc="upper right")

    if record_values:
        canvas.value("dim", dim)
        canvas.value("evalues", evalues)
        canvas.value("mean.contrib", l1)
        canvas.value("var.contrib", l2)
    return canvas


def plot_MclustDR(x: Any, dimens: Sequence[int] | None = None,
                  what: Sequence[str] = _DEFAULT_WHAT,
                  symbols: Sequence[Any] | None = None,
                  colors: Sequence[str] | None = None,
                  col_contour: str = "#B3B3B3",
                  ngrid: int = 200,
                  nlevels: int = 5,
                  asp: Any = None,
                  fig: Any = None) -> Canvas:
    """Plot a dimension reduction object as the non-interactive R path does.

    ``what`` takes the same names as the R argument. The panels are drawn in
    R's order: scatterplot, pairs, contour, classification, boundaries,
    density, evalues. Returns the canvas with the log.
    """
    canvas = Canvas()
    obj = x
    xdata = np.asarray(_get(obj, "x"), dtype=float)
    if xdata.ndim == 1:
        xdata = xdata.reshape(-1, 1)
    G = int(_get(obj, "G"))
    mixcomp = _get(obj, "mixcomp")
    obj_type = str(_get(obj, "type"))
    if obj_type == "Mclust":
        # R: class <- as.factor(object$classification), and as.numeric() of
        # that factor is the rank of each label among the sorted labels.
        y = np.asarray(mixcomp).astype(float).astype(int)
        levels = np.unique(y)
        cls = np.searchsorted(levels, y) + 1
    else:
        # R stores one label per observation for MclustDA. The translated
        # MclustDR keeps only the class levels, so these labels are not available.
        raise NotImplementedError(
            "MclustDA per-observation labels are not stored by the translated MclustDR")
    nclass = len(np.unique(cls))
    direc = np.asarray(_get(obj, "dir"), dtype=float)
    if direc.ndim == 1:
        direc = direc.reshape(-1, 1)
    numdir = int(_get(obj, "numdir"))

    if dimens is None:
        dims = np.arange(1, numdir + 1)
    else:
        dims = np.array([d for d in np.asarray(dimens, dtype=int).ravel() if 1 <= d <= numdir])
    if dims.size == 0:
        raise ValueError("invalid 'dimens' value(s) provided")

    opts_symbols = mclust_options("classPlotSymbols")
    opts_colors = mclust_options("classPlotColors")
    if symbols is None:
        if G <= len(opts_symbols):
            symbols = list(opts_symbols)
        elif G <= 26:
            symbols = _LETTERS
        else:
            raise ValueError("more symbols needed to show mixture components")
    symbols = list(symbols)
    if len(symbols) == 1:
        symbols = symbols * nclass
    if len(symbols) < nclass:
        symbols = [16] * nclass
    if colors is None:
        colors = list(opts_colors)
    colors = list(colors)
    if len(colors) == 1:
        colors = colors * nclass
    if len(colors) < nclass:
        colors = ["black"] * nclass

    what = list(dict.fromkeys(what))
    if "pairs" in what and dims.size == 2:
        what = ["scatterplot" if w == "pairs" else w for w in what]
    if dims.size == 1:
        what = [w if w in ("classification", "density", "evalues") else "classification"
                for w in what]
    what = list(dict.fromkeys(what))

    sym_pt = [symbols[c - 1] for c in cls]
    col_pt = [colors[c - 1] for c in cls]
    dir_sub = direc[:, dims - 1]
    cls_names = np.unique(cls)
    class2mixcomp = np.asarray(_get(obj, "class2mixcomp"), dtype=int)
    pro = np.asarray(_get(obj, "pro"), dtype=float)

    if "scatterplot" in what:
        ax = _axes(fig)
        canvas.window(ax, _range(dir_sub[:, 0]), _range(dir_sub[:, 1]))
        canvas.points(ax, dir_sub[:, 0], dir_sub[:, 1], pch=sym_pt, col=col_pt)

    if "pairs" in what:
        pairs_panels(canvas, fig, dir_sub, pch=sym_pt, col=col_pt, gap=0.2)

    if "contour" in what and dims.size >= 2:
        _contour(canvas, fig, obj, dims, cls, colors, sym_pt, col_pt, ngrid, nlevels,
                 nclass, class2mixcomp, pro, col_contour)

    if "classification" in what and obj_type == "Mclust":
        if dims.size == 1:
            _classification_1d(canvas, fig, direc, cls, colors, nclass)
        else:
            _classification_2d(canvas, fig, obj, dims, dir_sub, sym_pt, col_pt,
                               colors[:G], ngrid, G, mixcomp, "Mclust")
    if "classification" in what and obj_type in ("EDDA", "MclustDA") and dims.size >= 2:
        _classification_2d(canvas, fig, obj, dims, dir_sub, sym_pt, col_pt,
                           colors[:nclass], ngrid, nclass, mixcomp, obj_type)

    if "boundaries" in what and obj_type == "Mclust" and dims.size >= 2:
        _boundaries(canvas, fig, obj, dims, dir_sub, sym_pt, col_pt, ngrid, nclass)
    if "boundaries" in what and obj_type in ("EDDA", "MclustDA") and dims.size >= 2:
        _boundaries(canvas, fig, obj, dims, dir_sub, sym_pt, col_pt, ngrid, nclass)

    if "density" in what:
        _density(canvas, fig, obj, dims, cls, colors, ngrid, G, nclass, mixcomp, obj_type)

    if "evalues" in what:
        plotEvalues_MclustDR(obj, numdir=int(np.max(dims)), plot=True,
                             fig=fig, canvas=canvas, record_values=False)
    _ = cls_names
    return canvas


def _classification_1d(canvas: Canvas, fig: Any, direc: np.ndarray, cls: np.ndarray,
                       colors: Sequence[str], nclass: int) -> None:
    dir1 = direc[:, 0]
    n = dir1.size
    levels = np.unique(cls)
    groups = [dir1[cls == k] for k in levels]
    stats = np.column_stack([boxplot_stats(g) for g in groups])
    names = [str(k) for k in levels]
    ax = _axes(fig)
    canvas.boxplot(ax, stats, names, xlim=(0.0, nclass + 0.5), horizontal=True,
                   values_range=_range(dir1))
    canvas.points(ax, dir1, np.zeros(n), pch="|", col="black")


def _classification_2d(canvas: Canvas, fig: Any, obj: Any, dims: np.ndarray,
                       dir_sub: np.ndarray, sym_pt: Any, col_pt: Any,
                       palette: Sequence[str], ngrid: int, k: int, mixcomp: Any,
                       obj_type: str) -> None:
    dir2 = dir_sub[:, :2]
    pred = predict2D_MclustDR(obj, dim=dims[:2], ngrid=ngrid,
                              xlim=extendrange_05(dir2[:, 0]),
                              ylim=extendrange_05(dir2[:, 1]))
    classification = np.argmax(pred["z"], axis=2) + 1
    ax = _axes(fig)
    col = [adjustcolor_hex(c, 0.1) for c in palette[:k]]
    canvas.image(ax, pred["x"], pred["y"], classification, col=col)
    canvas.points(ax, dir2[:, 0], dir2[:, 1], pch=sym_pt, col=col_pt)


def _boundaries(canvas: Canvas, fig: Any, obj: Any, dims: np.ndarray,
                dir_sub: np.ndarray, sym_pt: Any, col_pt: Any, ngrid: int,
                nclass: int) -> None:
    dir2 = dir_sub[:, :2]
    pred = predict2D_MclustDR(obj, dim=dims[:2], ngrid=ngrid,
                              xlim=extendrange_05(dir2[:, 0]),
                              ylim=extendrange_05(dir2[:, 1]))
    unc = np.array(pred["uncertainty"], dtype=float)
    unc[0, :] = np.nan
    unc[ngrid - 1, :] = np.nan
    unc[:, 0] = np.nan
    unc[:, ngrid - 1] = np.nan
    palette = list(reversed(gray_colors(10, 0.0, 1.0)))
    breaks = np.linspace(0.0, 1.0 - 1.0 / nclass, 11)
    ax = _axes(fig)
    canvas.image(ax, pred["x"], pred["y"], unc, col=palette, breaks=breaks)
    canvas.points(ax, dir2[:, 0], dir2[:, 1], pch=sym_pt, col=col_pt)


def _density(canvas: Canvas, fig: Any, obj: Any, dims: np.ndarray, cls: np.ndarray,
             colors: Sequence[str], ngrid: int, G: int, nclass: int, mixcomp: Any,
             obj_type: str) -> None:
    d0 = int(dims[0])
    dir_all = np.asarray(_get(obj, "dir"), dtype=float)
    direc = dir_all[:, d0 - 1]
    par = projpar_MclustDR(obj, [d0])
    mu = np.asarray(par["mean"], dtype=float)[:, 0]
    sd = np.sqrt(np.asarray(par["variance"], dtype=float)[0, 0, :])
    xgrid = extendrange_01(direc)
    xgrid = np.linspace(xgrid.min(), xgrid.max(), 2 * ngrid)
    dens = np.column_stack([_dnorm(xgrid, mu[j], sd[j]) for j in range(G)])
    pro = np.asarray(_get(obj, "pro"), dtype=float)
    if obj_type != "Mclust":
        y = np.asarray(mixcomp)
        d = dens * pro[None, :]
        dens_out = np.zeros((xgrid.size, nclass))
        tab = _table_counts(y, cls, G, nclass)
        for i in range(nclass):
            j = np.where(tab[:, i] > 0)[0]
            dens_out[:, i] = d[:, j].sum(axis=1)
        dens = dens_out
    ax = _axes(fig)
    ylim = (min(0.0, float(np.min(dens * 1.1))), max(0.0, float(np.max(dens * 1.1))))
    canvas.window(ax, _range(xgrid), ylim)
    for j in range(dens.shape[1]):
        canvas.lines(ax, xgrid, dens[:, j], col=colors[j])


def _table_counts(y: np.ndarray, cls: np.ndarray, G: int, nclass: int) -> np.ndarray:
    """``table(y, class)`` with rows for the mixture components and columns for the classes."""
    tab = np.zeros((G, nclass))
    ys = y.astype(int)
    for a, b in zip(ys, cls):
        tab[a - 1, b - 1] += 1
    return tab


def _contour(canvas: Canvas, fig: Any, obj: Any, dims: np.ndarray, cls: np.ndarray,
             colors: Sequence[str], sym_pt: Any, col_pt: Any, ngrid: int, nlevels: int,
             nclass: int, class2mixcomp: np.ndarray, pro: np.ndarray,
             col_contour: str) -> None:
    d0, d1 = int(dims[0]), int(dims[1])
    direc = np.asarray(_get(obj, "dir"), dtype=float)
    dir2 = direc[:, [d0 - 1, d1 - 1]]
    par = projpar_MclustDR(obj, [d0, d1])
    means_all = np.asarray(par["mean"], dtype=float)
    var_all = np.asarray(par["variance"], dtype=float)
    ax = _axes(fig)
    usr = canvas.window(ax, _range(dir2[:, 0]), _range(dir2[:, 1]))
    for k in range(1, nclass + 1):
        idx = np.where(class2mixcomp == k)[0]
        pk = pro[idx] / pro[idx].sum()
        gx = _grid1(ngrid, usr[0], usr[1])
        gy = _grid1(ngrid, usr[2], usr[3])
        zz = _mixture_density(gx, gy, pk, means_all[idx, :], var_all[:, :, idx])
        levels = pretty(zz.ravel(), nlevels)
        canvas.contour(ax, gx, gy, zz, levels)
    canvas.points(ax, dir2[:, 0], dir2[:, 1], pch=sym_pt, col=col_pt)


def extendrange_05(x: Any) -> tuple[float, float]:
    """``extendrange(x, f = 0.05)``."""
    arr = np.asarray(x, dtype=float)
    lo, hi = float(arr.min()), float(arr.max())
    d = hi - lo
    return lo - 0.05 * d, hi + 0.05 * d


def extendrange_01(x: Any) -> np.ndarray:
    """``extendrange(x, f = 0.1)``."""
    arr = np.asarray(x, dtype=float)
    lo, hi = float(arr.min()), float(arr.max())
    d = hi - lo
    return np.array([lo - 0.1 * d, hi + 0.1 * d])
