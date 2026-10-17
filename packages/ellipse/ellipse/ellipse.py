"""Numerical and plotting routines from R's ellipse package."""

import numpy as np


def ellipse(
    x,
    scale=None,
    centre=(0.0, 0.0),
    level=0.95,
    t=None,
    which=(1, 2),
    npoints=100,
    center=None,
):
    """Return the outline of a two-dimensional confidence ellipse.

    This follows ``ellipse.default`` from R ellipse 0.5.0. ``which`` uses
    R's one-based matrix indices when ``x`` is a covariance/correlation matrix.
    """
    if center is None:
        center = centre
    if t is None:
        t = np.sqrt(-2.0 * np.log1p(-level))

    x_array = np.asarray(x)
    if x_array.ndim == 2:
        xind, yind = (int(which[0]) - 1, int(which[1]) - 1)
        r = x_array[xind, yind]
        if scale is None:
            scale_array = np.sqrt(
                np.asarray([x_array[xind, xind], x_array[yind, yind]])
            )
            if scale_array[0] > 0:
                r = r / scale_array[0]
            if scale_array[1] > 0:
                r = r / scale_array[1]
        else:
            scale_array = np.asarray(scale)
    else:
        r = np.min(x_array) if x_array.ndim else x_array
        scale_array = np.asarray((1.0, 1.0) if scale is None else scale)

    r = np.clip(r, -1.0, 1.0)
    d = np.arccos(r)
    angles = np.linspace(0.0, 2.0 * np.pi, int(npoints))
    result = np.column_stack(
        (
            t * scale_array[0] * np.cos(angles + d / 2.0) + center[0],
            t * scale_array[1] * np.cos(angles - d / 2.0) + center[1],
        )
    )
    return result


def plotcorr(
    corr,
    outline=True,
    col="grey",
    numbers=False,
    type="full",
    diag=None,
    bty="n",
    axes=False,
    xlab="",
    ylab="",
    asp=1,
    cex_lab=None,
    cex=0.75,
    mar=None,
    ax=None,
    **kwargs,
):
    """Plot a correlation matrix using the layout of ``ellipse::plotcorr``.

    The returned axes has ``_ellipse_data`` containing the cell coordinates,
    colors, and ellipse vertices, which is useful for data-level verification.
    """
    import matplotlib.pyplot as plt

    matrix = np.asarray(corr, dtype=float)
    if matrix.ndim != 2 or np.nanmin(matrix) < -1 - 1e-6 or np.nanmax(matrix) > 1 + 1e-6:
        raise ValueError("Need a correlation matrix")
    if type not in ("full", "lower", "upper"):
        raise ValueError("type must be one of full, lower, upper")
    if diag is None:
        diag = type == "full"
    if ax is None:
        _, ax = plt.subplots()
    nr, nc = matrix.shape
    rows = list(range(nr))
    cols = list(range(nc))
    xshift = yshift = 0
    if not diag and type == "upper":
        cols, rows, xshift = list(range(1, nc)), list(range(nr - 1)), 1
    elif not diag and type == "lower":
        cols, rows, yshift = list(range(nc - 1)), list(range(1, nr)), -1
    maxdim = max(len(rows), len(cols))
    ax.set_xlim(-0.5, maxdim + 0.5)
    ax.set_ylim(0.5, maxdim + 1.5)
    colors = np.resize(np.asarray(col, dtype=object), matrix.size).reshape(matrix.shape)
    cells = []
    for i in range(nr):
        for j in range(nc):
            selected = type == "full" or (type == "lower" and i >= j) or (type == "upper" and i <= j)
            if not selected or (i == j and not diag):
                continue
            xx, yy = j + 1 - xshift, len(rows) - i - yshift
            if numbers:
                ax.text(xx + 0.3, yy, str(int(np.rint(10 * matrix[i, j]))),
                        ha="right", fontsize=cex * 10)
                cells.append({"i": i, "j": j, "color": colors[i, j], "number": 10 * matrix[i, j]})
            else:
                mat = np.eye(2)
                mat[0, 1] = mat[1, 0] = matrix[i, j]
                vertices = ellipse(mat, t=0.43)
                vertices[:, 0] += xx
                vertices[:, 1] += yy
                ax.fill(vertices[:, 0], vertices[:, 1], color=colors[i, j])
                if outline:
                    ax.plot(vertices[:, 0], vertices[:, 1], color="black")
                cells.append({"i": i, "j": j, "color": colors[i, j], "vertices": vertices})
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.set_aspect("equal" if asp == 1 else asp)
    ax._ellipse_data = {"cells": cells, "xlim": ax.get_xlim(), "ylim": ax.get_ylim()}
    return ax


def pairs(x, labels=None, fig=None, **kwargs):
    """Draw a scatterplot matrix, corresponding to ``graphics::pairs``."""
    import matplotlib.pyplot as plt

    data = np.asarray(x, dtype=float)
    if data.ndim != 2:
        raise ValueError("x must be a matrix")
    n, d = data.shape
    if fig is None:
        fig = plt.figure()
    axes = np.empty((d, d), dtype=object)
    for row in range(d):
        for col in range(d):
            ax = fig.add_subplot(d, d, row * d + col + 1)
            axes[row, col] = ax
            if row == col:
                ax.hist(data[:, col], bins="auto", color="0.75")
            else:
                ax.scatter(data[:, col], data[:, row], s=12, c="black")
            ax.set_xlim(_r_range(data[:, col]))
            ax.set_ylim(_r_range(data[:, row]))
            ax.tick_params(labelbottom=(row == d - 1), labelleft=(col == 0))
    fig.subplots_adjust(wspace=0.2, hspace=0.2)
    fig._ellipse_pairs_data = {"axes": axes, "limits": [
        (tuple(ax.get_xlim()), tuple(ax.get_ylim())) for ax in axes.ravel()
    ]}
    return fig


def pairs_profile(x, labels=None, panel=None, invert=True, plot_tau=True,
                  plot_trace=True, plot_sketch=True, plot_ellipse=False,
                  level=0.95, fig=None, **kwargs):
    """Plot profile objects as a matrix of trace and confidence-ellipse panels.

    Each profile component is ``(tau, parameter_matrix)``; parameter matrices
    follow R's column convention.
    """
    import matplotlib.pyplot as plt

    components = list(x)
    npar = len(components) + int(plot_tau)
    if fig is None:
        fig = plt.figure(figsize=(2.4 * npar, 2.4 * npar))
    if labels is None:
        labels = [str(i + 1) for i in range(npar)]
    if len(labels) < npar:
        labels = list(labels) + [f"[{i}]" for i in range(len(labels), npar)]
    tau = np.concatenate([np.asarray(c[0], dtype=float).ravel() for c in components])
    records = []
    order = range(npar) if invert else range(npar - 1, -1, -1)
    for i in order:
        for j in range(npar):
            ax = fig.add_subplot(npar, npar, i * npar + j + 1)
            if i < len(components):
                yi = np.asarray(components[i][1], dtype=float)[:, i]
            else:
                yi = tau
            if j < len(components):
                xj = np.asarray(components[j][1], dtype=float)[:, j]
            else:
                xj = np.asarray(components[i][0], dtype=float).ravel() if i < len(components) else tau
            if i != j:
                if plot_trace:
                    if len(xj) == len(yi):
                        ax.plot(np.r_[xj, np.nan, xj], np.r_[yi, np.nan, yi], color="black")
                    else:
                        ax.plot(xj, np.full(len(xj), np.nan), color="black")
                if plot_sketch and i < len(components) and j < len(components):
                    z = ellipse(np.eye(2), which=(1, 2),
                                level=level, npoints=100)
                    ax.plot(z[:, 0], z[:, 1], color="black")
            else:
                ax.text(0.5, 0.5, labels[i], transform=ax.transAxes, ha="center", va="center")
            ax.set_xlim(_r_range(xj))
            ax.set_ylim(_r_range(yi))
            records.append({"i": i, "j": j, "x": xj, "y": yi, "xlim": ax.get_xlim(), "ylim": ax.get_ylim()})
    fig._ellipse_profile_data = records
    return fig


def _r_range(values):
    values = np.asarray(values, dtype=float)
    lo, hi = float(np.nanmin(values)), float(np.nanmax(values))
    if lo == hi:
        delta = 0.4 * abs(lo) if lo else 1.0
        lo, hi = lo - delta, hi + delta
    delta = hi - lo
    return lo - 0.04 * delta, hi + 0.04 * delta
