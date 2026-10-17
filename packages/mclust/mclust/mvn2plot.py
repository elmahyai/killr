"""mvn2plot: a two-dimensional Gaussian ellipse (mclust graphics.R, second definition).

The eigen decomposition uses LAPACK's dsyevr through scipy, as R's
``eigen(symmetric = TRUE)`` does, so the eigenvector signs and therefore the
order of the ellipse vertices match R.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np
from scipy.linalg import eigh

from .chull import chull as r_chull
from .plot_log import PlotLog, adjustcolor

__all__ = ["mvn2plot", "mvn2plot_vertices", "r_chull"]


def mvn2plot_vertices(mu: Any, sigma: Any, k: int = 15) -> dict[str, Any]:
    """The ellipse vertices, the principal axes and the centre, as mvn2plot computes them.

    ``xy`` holds the four quarter arcs in R's order (each of length k + 1),
    ``axes`` holds the two principal-axis segments (rows 0-1 and 2-3).
    """
    mu = np.asarray(mu, dtype=float).ravel()
    sigma = np.asarray(sigma, dtype=float)
    p = mu.size
    if p != 2:
        raise ValueError("only two-dimensional case is available")
    if sigma.shape != (2, 2):
        raise ValueError("mu and sigma are incompatible")
    vals, vecs = eigh(sigma, driver="evr", lower=True)
    order = np.argsort(vals)[::-1]
    s = np.sqrt(vals[order])
    V = vecs[:, order].T
    theta = np.arange(k + 1, dtype=float) * (math.pi / (2 * k))
    x = s[0] * np.cos(theta)
    y = s[1] * np.sin(theta)
    arc = np.column_stack([np.concatenate([x, -x, -x, x]),
                           np.concatenate([y, y, -y, -y])])
    xy = arc @ V + mu
    axes = np.column_stack([[s[0], -s[0], 0.0, 0.0],
                            [0.0, 0.0, s[1], -s[1]]]) @ V + mu
    return {"x": x, "xy": xy, "axes": axes, "V": V, "s": s, "mu": mu}


def mvn2plot(
    mu: Any,
    sigma: Any,
    k: int = 15,
    alone: bool = False,
    fillEllipse: bool = False,
    alpha: float = 0.3,
    col: Sequence[str] | None = None,
    pch: Any = 8,
    lty: Sequence[int] = (1, 2),
    lwd: Sequence[int] = (1, 1),
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """Draw one two-dimensional Gaussian ellipse with its principal axes and centre."""
    del lty, lwd
    if log is None:
        log = PlotLog()
    if col is None:
        col = ["grey30"] * 3
    elif isinstance(col, str):
        col = [col]
    geo = mvn2plot_vertices(mu, sigma, k)
    xy = geo["xy"]
    mu_v = geo["mu"]
    if alone:
        xymin = xy.min(axis=0)
        xymax = xy.max(axis=0)
        r = math.ceil(float(np.max(xymax - xymin)) / 2)
        xymid = (xymin + xymax) / 2
        log.window(ax, (-r + xymid[0], r + xymid[0]), (-r + xymid[1], r + xymid[1]),
                   xaxs="r", yaxs="r")
    if fillEllipse:
        col = list(col) * 3
        hull = r_chull(xy)
        log.polygon(ax, xy[hull, 0], xy[hull, 1], adjustcolor(col[0], alpha))
    else:
        lx = k + 1
        for q in range(4):
            seg = xy[q * lx:(q + 1) * lx]
            log.lines(ax, seg[:, 0], seg[:, 1], col=col[0])
    axes = geo["axes"]
    log.lines(ax, axes[0:2, 0], axes[0:2, 1], col=col[1])
    log.lines(ax, axes[2:4, 0], axes[2:4, 1], col=col[1])
    log.points(ax, [mu_v[0]], [mu_v[1]], pch, col[2])
