"""plot.rqss and plot.summary.rqss: the smooth-term panels of an rqss fit.

R/rqss.R of quantreg 6.1. Drawing is Matplotlib. Each smooth term is one panel:
a qss1 term is drawn as a line over its knots, a qts1 term as a step function,
and the pointwise or uniform bands are shaded. The drawing log follows the
format in quantreg.plot: T labels, L layout, W window, P points or a line,
Y polygon, V value. A title is logged as a T record with empty labels.

R draws each panel on its own page when pages is 0. The figure here puts the
panels in one grid, and the log is the same either way.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
from scipy.stats import t as t_dist

from quantreg.crit import critval
from quantreg.plot import _layout, _new_figure, _plot_xy, _polygon, _range, _window, canon_col, n2mfrow
from quantreg.rqss_methods import _predict_qss1, summary_rqss

# R's named colours for the band fills, as canon_col would write them.
_BAND_COLOURS = {"grey85": "#D9D9D9", "grey65": "#A6A6A6"}
SUMMARY_WARNING = "No plot method for summary.rqss objects:   plot the rqss object instead"


def _set_layout(m, pages):
    """SetLayout in plot.rqss: (rows, columns) of mfrow for m panels on pages, or None when pages is 0."""
    if pages > m:
        pages = m
    if pages < 0:
        pages = 0
    if pages == 0:
        return None
    q = m // pages
    if m % pages != 0:
        q += 1
        while q * (pages - 1) >= m:
            pages -= 1
    c = int(math.trunc(math.sqrt(q)))
    if c < 1:
        c = 1
    r = q // c
    if r < 1:
        r = 1
    while r * c < q:
        r += 1
    while r * c - q > c and r > 1:
        r -= 1
    while r * c - q > r and c > 1:
        c -= 1
    return r, c


def _line(ax, log, xs, ys, type_, colour="#000000"):
    """lines(x, y, type): the logged P record, then the line on the axes. Type n draws nothing."""
    xs = np.asarray(xs, dtype=float).ravel()
    ys = np.asarray(ys, dtype=float).ravel()
    if log is not None:
        log.record("P", xs, ys, [type_], [colour])
    if type_ == "S":
        ax.step(xs, ys, where="post", color=colour)
    elif type_ == "l":
        ax.plot(xs, ys, linestyle="-", color=colour)


def _title(ax, log, text):
    """title(main): a T record with empty labels, then the title."""
    if log is not None:
        log.record("T", [""], [""], [text])
    ax.set_title(text)


def _matplot_window(ax, log, xs, ymat, xlab, ylab):
    """matplot(x, y, type = "n"): labels, the window over every column, then the window record."""
    if log is not None:
        log.record("T", [xlab], [ylab], [""])
    lo_x, hi_x = _range(xs)
    lo_y, hi_y = _range(np.asarray(ymat, dtype=float))
    ax.set_xlim(*_window(lo_x, hi_x))
    ax.set_ylim(*_window(lo_y, hi_y))
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    if log is not None:
        log.record("W", [*ax.get_xlim(), *ax.get_ylim()])


def _rug(ax, xs, jit, rng):
    """rug(x) at the bottom of the panel. Not logged; R's jitter is random, so the positions are not compared."""
    values = np.asarray(xs, dtype=float).ravel()
    if jit:
        span = float(np.ptp(values)) or 1.0
        values = values + rng.uniform(-0.02, 0.02, size=values.size) * span
    low = ax.get_ylim()[0]
    ax.plot(values, np.full(values.size, low), linestyle="none", marker="|", color="black", markersize=4)


def _recycled_divide(matrix, norms):
    """matrix / norms as R writes it: norms is a vector of one value per column, and R recycles it.

    In plot.rqss, sqrt(apply(BX^2, 2, sum)) has one value per column of the p x 399
    matrix, but R divides the whole matrix by it. Column-major, element k is divided by
    norms[k mod length(norms)]. The uniform band is computed this way in R, so this
    keeps that result rather than the per-column normalisation.
    """
    flat = np.asarray(matrix, dtype=float).ravel(order="F")
    divisor = np.asarray(norms, dtype=float).reshape(-1)
    return (flat / divisor[np.arange(flat.size) % divisor.size]).reshape(matrix.shape, order="F")


def _summary_qss1(xyz, V, rdf, coverage, bands):
    """summary.qss1 inside plot.rqss: the grid, the fitted values, se and the critical values cv."""
    xyz = np.asarray(xyz, dtype=float)
    knots = xyz[:, 0]
    eps = 0.01
    ngrid = 400
    grid = np.linspace(knots.min() + eps, knots.max() - eps, ngrid)
    fitted, design_part = _predict_qss1(xyz, grid)
    design = np.hstack([np.ones((ngrid, 1)), design_part])
    S = design @ V @ design.T
    se = np.sqrt(np.diag(S))
    cv = np.array([float(t_dist.ppf(1.0 - (1.0 - coverage) / 2.0, rdf))])
    if bands in ("uniform", "both"):
        values, vectors = np.linalg.eigh(V)
        root = vectors @ np.diag(np.sqrt(np.maximum(0.0, values))) @ vectors.T
        BX1 = _recycled_divide(root @ design[1:].T, np.sqrt(np.sum((root @ design[1:].T) ** 2, axis=0)))
        BX0 = _recycled_divide(root @ design[:-1].T, np.sqrt(np.sum((root @ design[:-1].T) ** 2, axis=0)))
        kappa = float(np.sum(np.sqrt(np.sum((BX1 - BX0) ** 2, axis=0))))
        cvu = critval(kappa, alpha=1.0 - coverage, rdf=rdf)
        cv = np.array([cvu, cv[0]]) if bands == "both" else np.array([cvu])
    return grid, fitted, se, cv


def plot_rqss(
    x,
    rug=True,
    jit=True,
    bands=None,
    coverage=0.95,
    add=False,
    shade=True,
    select=None,
    pages=0,
    titles=None,
    bcol=None,
    fig=None,
    log=None,
):
    """plot.rqss: one panel per smooth term, with the intercept added to the effect.

    x is an rqss object (rqss in this package). bands is None, "pointwise",
    "uniform" or "both". Returns a list with one entry per smooth term: None when
    the term is not drawn with bands, else a dict with x, blo and bhi (R's
    rqssband). The intercept is needed for the bands.
    """
    qss = list(x.qss)
    m = len(qss)
    if m == 0:
        raise ValueError("No qss object to plot")
    if select is not None and len(select) > 0:
        select = [int(item) for item in select]
        if not all(1 <= item <= m for item in select):
            raise ValueError(f"select must be in 1:{m}")
        layout_count = len(select)
    else:
        select = list(range(1, m + 1))
        layout_count = m
    layout = _set_layout(layout_count, pages)
    qssnames = list(x.qssnames)
    if titles is not None:
        if len(titles) != len(qssnames):
            raise ValueError("Length of titles doesn't match length of qssnames")
    else:
        titles = [f"Effect of  {name}" for name in qssnames]
    coef = np.asarray(x.coef, dtype=float).reshape(-1)
    names = list(x.coef_names)

    band_out = [None] * m
    use_bands = bool(bands)
    V_list = None
    rdf = None
    if use_bands:
        rdf = int(x.n) - int(x.edf)
        if "(Intercept)" not in names:
            raise ValueError("rqss confidence bands require an intercept parameter")
        if m == 1:
            raise ValueError("subscript out of bounds: summary.rqss has no Vqss for one smooth term")
        V_list = summary_rqss(x, cov=True)["Vqss"]
        if bcol is None or len(bcol) == 0:
            bcol = ["grey85", "grey65"]
    intercept = float(coef[names.index("(Intercept)")]) if use_bands else float(coef[0])
    rng = np.random.default_rng(1)

    if fig is None:
        fig = _new_figure(None)
    if layout is not None:
        _layout(log, layout[0], layout[1])
        grid_rows, grid_cols = layout
    else:
        grid_rows, grid_cols = n2mfrow(len(select))

    for position, i in enumerate(select):
        component = qss[i - 1]
        if add and fig.axes:
            ax = fig.axes[-1]
        else:
            ax = fig.add_subplot(grid_rows, grid_cols, position + 1)
        xyz = np.asarray(component.xyz, dtype=float)
        knots = xyz[:, 0]
        values = xyz[:, 1]
        if int(component.Dorder) == 0:
            # plot.qts1: a step function, labels left at their defaults
            fitted = intercept + values
            if not add:
                _plot_xy(ax, log, knots, fitted, type_="S", xlab="", ylab="")
            _line(ax, log, knots, fitted, "S")
            if rug:
                _rug(ax, knots, jit, rng)
        elif not use_bands:
            # plot.qss1: a line over the knots, labelled as the term
            fitted = intercept + values
            if not add:
                _plot_xy(ax, log, knots, fitted, type_="n", xlab=qssnames[i - 1], ylab="Effect")
            _line(ax, log, knots, fitted, "l")
            if rug:
                _rug(ax, knots, jit, rng)
        else:
            grid, fitted_grid, se, cv = _summary_qss1(xyz, V_list[i - 1], rdf, coverage, bands)
            mean = fitted_grid + intercept
            for k, cvk in enumerate(cv):
                name = bcol[min(k, len(bcol) - 1)]
                colour = canon_col(_BAND_COLOURS.get(name, name))
                lo = mean - cvk * se
                hi = mean + cvk * se
                if add or k > 0:
                    if shade:
                        _polygon(ax, log, np.concatenate([grid, grid[::-1]]), np.concatenate([lo, hi[::-1]]), colour)
                    else:
                        ax.plot(grid, mean + cvk * (-se), linestyle="--", color="blue")
                        ax.plot(grid, mean + cvk * se, linestyle="--", color="blue")
                else:
                    ymat = np.column_stack([mean + cvk * (-se), mean + cvk * se])
                    _matplot_window(ax, log, grid, ymat, qssnames[i - 1], "Effect")
                    if shade:
                        _polygon(ax, log, np.concatenate([grid, grid[::-1]]), np.concatenate([lo, hi[::-1]]), colour)
                    else:
                        widths = np.resize(np.asarray(cv, dtype=float), se.size) * se
                        ax.plot(grid, mean + widths, linestyle="--", color="black")
                        ax.plot(grid, mean - widths, linestyle="--", color="black")
                _line(ax, log, grid, mean, "l")
            band_out[i - 1] = {
                "x": grid,
                "blo": mean[:, None] - se[:, None] * np.asarray(cv, dtype=float)[None, :],
                "bhi": mean[:, None] + se[:, None] * np.asarray(cv, dtype=float)[None, :],
            }
            if rug:
                _rug(ax, xyz[:, 0], jit, rng)
        _title(ax, log, titles[i - 1])
    return band_out


def _qss2_plot_xyz(x):
    """The n x 3 matrix (x, y, z) of a qss2 object, as plot.qss2 reads x."""
    if isinstance(x, dict):
        xyz = x.get("xyz", x)
    else:
        xyz = getattr(x, "xyz", x)
    xyz = np.asarray(xyz, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3:
        raise ValueError("plot.qss2 needs an n x 3 matrix (x, y, z)")
    return xyz


def plot_qss2(x, render="contour", ncol=100, zcol=None, fig=None, log=None, **kwargs):
    """plot.qss2: the qss2 surface drawn as contours of its interpolated grid.

    x is the n x 3 matrix (x, y, z), or a qss2 object with an xyz matrix. The
    default render is "contour": the points are plotted with no marks, the
    interp grid of the fit (interp's default 40 by 40 grid) is drawn as contour
    lines, and the convex hull of the triangulation is drawn over it. Returns the
    hull as a dict with x, y and the 1-based index i, as R's convex.hull returns.

    The contour lines are Matplotlib's, not R's contourLines, so only the grid and
    the hull are checked against R. The R levels, the persp and rgl renders are not
    translated: render "persp" and "rgl" raise NotImplementedError. Other values of
    render raise ValueError, as R's stop does. ncol, zcol and the extra graphical
    arguments are accepted and not drawn.
    """
    from interp.convex_hull import convex_hull
    from interp.interp import interp as interp_grid
    from interp.tri_mesh import tri_mesh

    del ncol, zcol, kwargs
    xyz = _qss2_plot_xyz(x)
    px = xyz[:, 0]
    py = xyz[:, 1]
    pz = xyz[:, 2]
    trinew = tri_mesh(px, py)
    if render == "rgl":
        raise NotImplementedError('render = "rgl" is not translated: rgl is routed to Plotly')
    if render == "persp":
        raise NotImplementedError('render = "persp" is not translated: it returns the viewing matrix of R graphics')
    if render != "contour":
        raise ValueError(f"Unable to render:  {render}")

    fig = _new_figure(fig)
    ax = fig.add_subplot(1, 1, 1)
    _plot_xy(ax, log, px, py, type_="n", xlab="x", ylab="y")
    grid = interp_grid(px, py, pz)
    xo = np.asarray(grid["x"], dtype=float).reshape(-1)
    yo = np.asarray(grid["y"], dtype=float).reshape(-1)
    zo = np.asarray(grid["z"], dtype=float).reshape(xo.size, yo.size)
    na = np.isnan(zo)
    if log is not None:
        log.record("V", ["xo"], xo)
        log.record("V", ["yo"], yo)
        log.record("V", ["zo"], np.where(na, 0.0, zo).ravel(order="F"))
        log.record("V", ["zna"], na.astype(float).ravel(order="F"))
    ax.contour(xo, yo, np.ma.masked_invalid(zo.T))

    hull = convex_hull(trinew)
    hx = np.asarray(hull["x"], dtype=float)
    hy = np.asarray(hull["y"], dtype=float)
    ax.plot(np.append(hx, hx[0]), np.append(hy, hy[0]), linestyle="-", color="#000000")
    if log is not None:
        log.record("V", ["hull_x"], hx)
        log.record("V", ["hull_y"], hy)
        log.record("V", ["hull_i"], np.asarray(hull["i"], dtype=float))
    return hull


def plot_summary_rqss(x=None, **kwargs):
    """plot.summary.rqss has no plot: it warns and draws nothing."""
    warnings.warn(SUMMARY_WARNING, stacklevel=2)
    return None
