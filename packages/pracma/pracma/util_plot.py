"""Plotting helpers. Matplotlib draws; the series are also stored for checks."""

from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

from pracma._util import PracmaError
from pracma.elementary import deg2rad, hypot, linspace
from pracma.util_grid import meshgrid
from pracma.util_session import _figures
from pracma.util_support import is_numeric, r_seq, require

_drawn: dict = {}


def _remember(value):
    _drawn["value"] = np.asarray(value, dtype=float)
    return _drawn["value"]


def _figure():
    fig = plt.figure()
    _figures[fig.number] = fig
    return fig


def _line_style(lty):
    styles = {1: "solid", 2: "dashed", 3: "dotted", 4: "dashdot", "solid": "solid", "dashed": "dashed", "dotted": "dotted"}
    return styles.get(lty, "solid")


def semilogx(x, y, **kwargs):
    _figure()
    plt.semilogx(x, y, **kwargs)
    plt.grid(True)
    _remember(y)
    return None


def semilogy(x, y, **kwargs):
    _figure()
    plt.semilogy(x, y, **kwargs)
    plt.grid(True)
    _remember(y)
    return None


def loglog(x, y, **kwargs):
    _figure()
    plt.loglog(x, y, **kwargs)
    plt.grid(True)
    _remember(y)
    return None


def plotyy(
    x1,
    y1,
    x2,
    y2,
    gridp=True,
    box_col="grey",
    type="l",
    lwd=1,
    lty=1,
    xlab="x",
    ylab="y",
    main="",
    col_y1="navy",
    col_y2="maroon",
    **kwargs,
):
    require(is_numeric(x1) and is_numeric(y1) and is_numeric(x2) and is_numeric(y2), "is.numeric(x1) is not TRUE")
    left = np.asarray(y1, dtype=float).reshape(-1)
    right = np.asarray(y2, dtype=float).reshape(-1)
    y1_low, y1_high = float(np.min(left)), float(np.max(left))
    y2_low, y2_high = float(np.min(right)), float(np.max(right))
    span = y2_high - y2_low
    if span == 0:
        span = 1.0

    def transform(y):
        return y1_low + (np.asarray(y, dtype=float) - y2_low) / span * (y1_high - y1_low)

    _figure()
    style = "-" if type in ("l", "solid", 1) else "None"
    plt.plot(x1, left, color=col_y1, linewidth=lwd, linestyle=_line_style(lty) if style == "-" else "None")
    plt.plot(x2, transform(right), color=col_y2, linewidth=lwd, linestyle=_line_style(lty))
    plt.xlabel(xlab)
    plt.ylabel(ylab)
    plt.title(main)
    plt.box(True)
    if gridp:
        plt.grid(True)
    ax2 = plt.gca().twinx()
    ax2.plot(x2, right, color=col_y2, linewidth=lwd, linestyle=_line_style(lty))
    _remember(np.concatenate([left, right]))
    return None


def fplot(fn, interval, **kwargs):
    require(is_numeric(interval), "is.numeric(interval) is not TRUE")
    bounds = np.asarray(interval, dtype=float).reshape(-1)
    require(bounds.size == 2, "length(interval) == 2 is not TRUE")
    ezplot(fn, bounds[0], bounds[1], main="", **kwargs)
    return None


def ezplot(
    fn,
    a,
    b,
    n=101,
    col="blue",
    add=False,
    lty=1,
    lwd=1,
    marker=0,
    pch=1,
    grid=True,
    gridcol="gray",
    fill=False,
    fillcol="lightgray",
    xlab="x",
    ylab="f (x)",
    main="Function Plot",
    **kwargs,
):
    require(is_numeric(a), "is.numeric(a) is not TRUE")
    require(is_numeric(b), "is.numeric(b) is not TRUE")
    require(np.asarray(a).size == 1, "length(a) == 1 is not TRUE")
    require(np.asarray(b).size == 1, "length(b) == 1 is not TRUE")
    start = float(np.asarray(a).reshape(-1)[0])
    stop = float(np.asarray(b).reshape(-1)[0])
    require(start < stop, "a < b is not TRUE")
    x = r_seq(start, stop, int(n))
    y = np.asarray(fn(x), dtype=float).reshape(-1)
    if not add:
        _figure()
        plt.xlabel(xlab)
        plt.ylabel(ylab)
        plt.title(main)
    if grid:
        plt.grid(True, color=gridcol)
    if fill:
        plt.fill_between(x, 0, y, color=fillcol)
    plt.plot(x, y, color=col, linestyle=_line_style(lty), linewidth=lwd)
    if marker and marker > 0:
        count = min(max(int(marker), 3), int(n) // 3)
        steps = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2)
        distance = np.concatenate([[0.0], np.cumsum(steps)])
        total = distance[-1]
        spacing = total / (count - 1) if count > 1 else total
        picks = [0, len(x) - 1]
        for step in range(1, count - 1):
            picks.insert(-1, int(np.argmin(np.abs(distance - step * spacing))))
        plt.plot(x[picks], y[picks], linestyle="None", marker="o", color=col)
    _remember(y)
    return None


def _grid_values(fn, xlim, ylim, n):
    require(is_numeric(xlim), "is.numeric(xlim) is not TRUE")
    require(is_numeric(ylim), "is.numeric(ylim) is not TRUE")
    x_bounds = np.asarray(xlim, dtype=float).reshape(-1)
    y_bounds = np.asarray(ylim, dtype=float).reshape(-1)
    require(x_bounds.size == 2, "length(xlim) == 2 is not TRUE")
    require(y_bounds.size == 2, "length(ylim) == 2 is not TRUE")
    require(x_bounds[0] < x_bounds[1], "xlim[1] < xlim[2] is not TRUE")
    require(y_bounds[0] < y_bounds[1], "ylim[1] < ylim[2] is not TRUE")
    xx = linspace(x_bounds[0], x_bounds[1], n)
    yy = linspace(y_bounds[0], y_bounds[1], n)
    values = np.empty((int(n), int(n)), dtype=float)
    for i in range(int(n)):
        for j in range(int(n)):
            values[i, j] = float(np.asarray(fn([xx[i], yy[j]])).reshape(-1)[0])
    return xx, yy, values


def ezcontour(fn, xlim=None, ylim=None, n=60, filled=False, col=None):
    if xlim is None:
        xlim = [-math.pi, math.pi]
    if ylim is None:
        ylim = [-math.pi, math.pi]
    xx, yy, values = _grid_values(fn, xlim, ylim, n)
    _figure()
    # Matplotlib's contour expects rows along y. The stored matrix keeps R's
    # layout, F[i, j] = f(c(xx[i], yy[j])).
    if filled:
        colors = col if col is not None else plt.cm.hot(np.linspace(0, 1, 12))
        plt.imshow(
            values.T,
            origin="lower",
            extent=[float(xx[0]), float(xx[-1]), float(yy[0]), float(yy[-1])],
            aspect="auto",
            cmap="hot" if col is None else None,
        )
        plt.contour(xx, yy, values.T, colors="black")
    else:
        plt.contour(xx, yy, values.T, colors="black" if col is None else col)
        plt.grid(True)
    _remember(values)
    return None


def ezsurf(fn, xlim=None, ylim=None, n=60, **kwargs):
    if xlim is None:
        xlim = [-math.pi, math.pi]
    if ylim is None:
        ylim = [-math.pi, math.pi]
    xx, yy, values = _grid_values(fn, xlim, ylim, n)
    grid_x, grid_y = np.meshgrid(xx, yy)
    fig = _figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(grid_x, grid_y, values.T, cmap="terrain", edgecolor="grey", linewidth=0.2)
    _remember(values)
    return None


def ezmesh(fn, xlim=None, ylim=None, n=60, **kwargs):
    if xlim is None:
        xlim = [-math.pi, math.pi]
    if ylim is None:
        ylim = [-math.pi, math.pi]
    xx, yy, values = _grid_values(fn, xlim, ylim, n)
    grid_x, grid_y = np.meshgrid(xx, yy)
    fig = _figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(grid_x, grid_y, values.T, color="yellow", edgecolor="grey", linewidth=0.3, alpha=0.9)
    _remember(values)
    return None


def polar(t, r, type="l", col="blue", grcol="darkgrey", bxcol="black", main="Polar Plot", add=False, **kwargs):
    require(is_numeric(t), "is.numeric(t) is not TRUE")
    require(is_numeric(r), "is.numeric(r) is not TRUE")
    theta = np.asarray(t, dtype=float).reshape(-1)
    radius = np.asarray(r, dtype=float).reshape(-1)
    if theta.size != radius.size:
        raise PracmaError("Arguments 't', 'r' have to be vectors of equal length.")
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    if not add:
        reach = hypot(x, y)
        mad = float(np.max(np.abs(MaxNLocator(nbins=4, min_n_ticks=3).tick_values(0, float(np.max(reach))))))
        if not np.isfinite(mad) or mad == 0:
            mad = 1.0
        _figure()
        plt.plot([-mad, mad], [-mad, mad], linestyle="None")
        plt.gca().set_aspect("equal")
        plt.axis("off")
        plt.title(main)
        phi = deg2rad(np.arange(0, 361, 2))
        for ring in MaxNLocator(nbins=4, min_n_ticks=3).tick_values(0, mad):
            plt.plot(ring * np.cos(phi), ring * np.sin(phi), color=grcol, linestyle=":")
        plt.axhline(0, color=grcol, linestyle=":")
        plt.axvline(0, color=grcol, linestyle=":")
        for spine in plt.gca().spines.values():
            spine.set_visible(True)
            spine.set_color(bxcol)
    style = {"l": "-", "p": "None", "n": "None"}.get(type, "-")
    marker = "o" if type == "p" else None
    plt.plot(x, y, linestyle=style, marker=marker, color=col)
    _remember(np.column_stack([x, y]))
    return None


def ezpolar(fun, interv=None):
    if interv is None:
        interv = [0, 2 * math.pi]
    require(is_numeric(interv), "is.numeric(interv) is not TRUE")
    bounds = np.asarray(interv, dtype=float).reshape(-1)
    if bounds.size != 2 or bounds[0] >= bounds[1]:
        raise PracmaError("Argument 'interv' must have two elements [a, b] with a < b.")
    count = 91
    theta = r_seq(bounds[0], bounds[1], count)
    try:
        radius = np.asarray(fun(theta), dtype=float).reshape(-1)
    except Exception:
        radius = np.array([])
    if radius.size != count:
        radius = np.array([float(fun(value)) for value in theta])
    polar(theta, radius)
    _remember(radius)
    return None


def errorbar(x, y, xerr=None, yerr=None, bar_col="red", bar_len=0.01, grid=True, with_=True, add=False, **kwargs):
    require(is_numeric(x), "is.numeric(x) is not TRUE")
    require(is_numeric(y), "is.numeric(y) is not TRUE")
    x_values = np.asarray(x, dtype=float).reshape(-1)
    y_values = np.asarray(y, dtype=float).reshape(-1)
    if x_values.size != y_values.size:
        raise PracmaError("Arguments 'x' and 'y' must be numeric vectors of equal length.")
    if xerr is not None:
        x_err = np.asarray(xerr, dtype=float).reshape(-1)
        if x_err.size not in (1, x_values.size):
            raise PracmaError("Argument 'xerr' must be a vector the same length as 'x'.")
    else:
        x_err = None
    if yerr is not None:
        y_err = np.asarray(yerr, dtype=float).reshape(-1)
        if y_err.size not in (1, y_values.size):
            raise PracmaError("Argument 'yerr' must be a vector the same length as 'y'.")
    else:
        y_err = None
    if not add:
        _figure()
        plt.plot(x_values, y_values, marker="o", linestyle="None")
        if grid:
            plt.grid(True)
    if y_err is not None:
        plt.vlines(x_values, y_values - y_err, y_values + y_err, color=bar_col)
    if x_err is not None:
        plt.hlines(y_values, x_values - x_err, x_values + x_err, color=bar_col)
    if with_:
        x_span = (np.max(x_values + (0 if x_err is None else np.abs(x_err))) - np.min(x_values - (0 if x_err is None else np.abs(x_err))))
        y_span = (np.max(y_values + (0 if y_err is None else np.abs(y_err))) - np.min(y_values - (0 if y_err is None else np.abs(y_err))))
        cap_x = bar_len * x_span / 2.0
        cap_y = bar_len * y_span / 2.0
        if y_err is not None:
            plt.hlines(y_values - y_err, x_values - cap_x, x_values + cap_x, color=bar_col)
            plt.hlines(y_values + y_err, x_values - cap_x, x_values + cap_x, color=bar_col)
        if x_err is not None:
            plt.vlines(x_values - x_err, y_values - cap_y, y_values + cap_y, color=bar_col)
            plt.vlines(x_values + x_err, y_values - cap_y, y_values + cap_y, color=bar_col)
    series = y_values
    if y_err is not None:
        series = np.concatenate([y_values, y_values - y_err, y_values + y_err])
    _remember(series)
    return None


def _andrews_y(A, npts):
    rows, cols = A.shape
    xpts = r_seq(0, 2 * math.pi, npts)
    curves = np.empty((rows, npts), dtype=float)
    for i in range(rows):
        xs = A[i, :]
        ypts = []
        for angle in xpts:
            value = xs[0]
            for j in range(1, cols):
                harmonic = (j + 1) // 2
                if (j + 1) % 2 == 1:
                    value = value + xs[j] * math.sin(harmonic * angle)
                else:
                    value = value + xs[j] * math.cos(harmonic * angle)
            ypts.append(value)
        curves[i, :] = ypts
    return xpts, curves


def andrewsplot(A, f, style="pol", scaled=False, npts=101):
    require(is_numeric(A), "is.numeric(A) is not TRUE")
    array = np.asarray(A, dtype=float)
    if array.ndim != 2:
        raise PracmaError("is.matrix(A) is not TRUE")
    if scaled:
        raise PracmaError('could not find function "scaled"')
    groups = np.asarray(f)
    if groups.dtype == bool or not np.issubdtype(groups.dtype, np.integer):
        if isinstance(f, (list, tuple)) and all(type(item) is int for item in f):
            groups = np.array(f, dtype=int)
        else:
            raise PracmaError("Argument 'f' must be a factor or an integer vector.")
    rows, cols = array.shape
    if cols < 2 or rows < 2:
        raise PracmaError("Matrix 'A' must have at least two rows and columns.")
    xpts, curves = _andrews_y(array, int(npts))
    palette = ["black", "red", "green", "blue", "cyan", "magenta", "yellow", "gray"]
    if style == "cart":
        _figure()
        plt.title("Andrews' Curves")
        for index in np.random.permutation(rows):
            color = palette[(int(groups.reshape(-1)[index]) - 1) % len(palette)]
            plt.plot(xpts, curves[index, :], color=color)
    elif style == "pol":
        limit = float(np.max(np.abs(curves)))
        polar([0], [limit], type="n", main="Andrews' Curves", bxcol="white")
        for index in np.random.permutation(rows):
            color = palette[(int(groups.reshape(-1)[index]) - 1) % len(palette)]
            polar(xpts, curves[index, :], col=color, add=True)
    else:
        raise PracmaError("Argument 'style' can only be 'cart' or 'pol'.")
    _remember(curves)
    return None


def quiver(x, y, u, v, scale=0.05, angle=10, length=0.1, **kwargs):
    require(is_numeric(x) and is_numeric(y) and is_numeric(u) and is_numeric(v), "is.numeric(x) is not TRUE")
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    u_values = np.asarray(u, dtype=float)
    v_values = np.asarray(v, dtype=float)
    if not plt.get_fignums():
        _figure()
    color = kwargs.get("col", kwargs.get("color", "green"))
    x_end = x_values + scale * u_values
    y_end = y_values + scale * v_values
    plt.quiver(
        x_values,
        y_values,
        x_end - x_values,
        y_end - y_values,
        angles="xy",
        scale_units="xy",
        scale=1,
        color=color,
    )
    _remember(np.concatenate([np.asarray(x_end, dtype=float).reshape(-1), np.asarray(y_end, dtype=float).reshape(-1)]))
    return None


def vectorfield(fun, xlim, ylim, n=16, scale=0.05, col="green", **kwargs):
    require(is_numeric(xlim), "is.numeric(xlim) is not TRUE")
    require(np.asarray(xlim).size == 2, "length(xlim) == 2 is not TRUE")
    require(is_numeric(ylim), "is.numeric(ylim) is not TRUE")
    require(np.asarray(ylim).size == 2, "length(ylim) == 2 is not TRUE")
    x_bounds = np.asarray(xlim, dtype=float).reshape(-1)
    y_bounds = np.asarray(ylim, dtype=float).reshape(-1)
    xpts = linspace(x_bounds[0], x_bounds[1], n)
    ypts = linspace(y_bounds[0], y_bounds[1], n)
    grid = meshgrid(xpts, ypts)
    px = np.ones((int(n), int(n)))
    py = np.asarray(fun(grid["X"], grid["Y"]), dtype=float)
    _figure()
    plt.plot(x_bounds, y_bounds, linestyle="None")
    plt.xlim(x_bounds[0], x_bounds[1])
    plt.ylim(y_bounds[0], y_bounds[1])
    plt.grid(True)
    quiver(grid["X"], grid["Y"], px, py, scale=scale, col=col)
    _remember(py)
    return None
