"""surfacePlot: density or uncertainty surface over a grid (mclust graphics.R).

The grid, the density and the uncertainty come from the numeric inputs only:
``parameters`` is a plain dict with ``pro``, ``mean`` (d by G) and
``variance`` = {``sigma``: d by d by G}. The drawing goes through ``PlotLog``.

Colour palettes are not compared; the
default palettes are Matplotlib approximations of R's hcl.colors and
blue2grey.colors.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

import numpy as np

from matplotlib import colormaps
from matplotlib.colors import to_hex

from .cdens_v_vei_vev_vii_vvi_vvv import cdensVVV
from .logsumexp import logsumexp
from .plot_log import PlotLog, adjustcolor, grid1, grid2, r_seq_len
from .softmax import softmax
from .utility_functions import hdrlevels
from ._plot_common import pretty

__all__ = ["surfacePlot"]

_TYPES = ("contour", "hdr", "image", "persp")
_WHAT = ("density", "uncertainty")
_TRANSF = ("none", "log", "sqrt")


def _densNuncer(data: np.ndarray, pro: np.ndarray, mu: np.ndarray, sigma: np.ndarray):
    """mclust's densNuncer for the VVV model: density and uncertainty per row of data."""
    G = sigma.shape[2]
    chol = np.stack([np.linalg.cholesky(sigma[:, :, g]).T for g in range(G)], axis=2)
    params = {"pro": pro, "mean": mu, "variance": {"sigma": sigma, "cholsigma": chol}}
    cden = np.asarray(cdensVVV(data=data, logarithm=True, parameters=params), dtype=float)
    logpro = np.log(pro)
    logden = np.asarray(logsumexp(cden, logpro), dtype=float).ravel()
    z = np.asarray(softmax(cden, logpro), dtype=float)
    return np.exp(logden), 1.0 - z.max(axis=1)


def _default_col_palette(n: int) -> list[str]:
    """Approximation of hcl.colors(n, "blues", rev = TRUE)."""
    cmap = colormaps["Blues_r"]
    return [to_hex(cmap(v)) for v in np.linspace(0.0, 1.0, n)]


def _default_hdr_palette(n: int) -> list[str]:
    """Approximation of blue2grey.colors (a Lab ramp in R; sRGB here)."""
    base = np.array([[0xE6, 0xE6, 0xE6], [0xBC, 0xC9, 0xD1], [0x6C, 0x7F, 0x97], [0x3E, 0x52, 0x64]],
                    dtype=float) / 255.0
    t = np.linspace(0.0, 1.0, n)
    pos = t * (len(base) - 1)
    out = []
    for p in pos:
        k = min(int(np.floor(p)), len(base) - 2)
        f = p - k
        rgb = base[k] * (1 - f) + base[k + 1] * f
        out.append(to_hex(rgb))
    return out


def surfacePlot(
    data: Any,
    parameters: dict,
    what: str = "density",
    type: str = "contour",
    transformation: str = "none",
    grid: int | Sequence[int] = 200,
    nlevels: int = 11,
    levels: Sequence[float] | None = None,
    prob: Sequence[float] = (0.25, 0.5, 0.75),
    col: str = "#808080",
    col_palette: Callable[[int], Sequence[str]] | None = None,
    hdr_palette: Callable[[int], Sequence[str]] | None = None,
    xlim: Sequence[float] | None = None,
    ylim: Sequence[float] | None = None,
    main: bool = False,
    scale: bool = False,
    swapAxes: bool = False,
    verbose: bool = False,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> dict[str, np.ndarray]:
    """Draw the density or uncertainty over a grid as a contour, HDR, image or perspective plot.

    Returns the grid ``x``, ``y`` and the transformed surface ``z``, as R's
    invisible list does.
    """
    del main, verbose
    if log is None:
        log = PlotLog()
    X = np.asarray(data, dtype=float)
    if X.ndim != 2 or X.shape[1] != 2:
        raise ValueError("data must be two dimensional")
    if type == "level":
        type = "hdr"
    if type not in _TYPES:
        raise ValueError("type improperly specified")
    if what not in _WHAT:
        raise ValueError("what improperly specified")
    if transformation not in _TRANSF:
        raise ValueError("transformation improperly specified")
    pro = parameters.get("pro")
    mu = parameters.get("mean")
    sigma = parameters["variance"].get("sigma")
    have = mu is not None and sigma is not None and pro is not None
    if not have:
        raise ValueError("need parameters to compute density")
    mu = np.asarray(mu, dtype=float)
    if mu.ndim == 1:
        mu = mu.reshape(-1, 1)
    sigma = np.asarray(sigma, dtype=float)
    pro = np.asarray(pro, dtype=float).ravel()
    if sigma.ndim != 3 or mu.shape[1] != sigma.shape[2]:
        raise ValueError("means and variance parameters are incompatible")
    if swapAxes:
        # This is the coordinate permutation used by R.  R's pro[2:1]
        # only makes sense for the two-component case; retaining all
        # components for larger mixtures is the useful, well-defined
        # extension (the component labels are not coordinate-dependent).
        X = X[:, ::-1]
        mu = mu[::-1, :]
        sigma = sigma[::-1, ::-1, :]
        if pro.size == 2:
            pro = pro[::-1]

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

    if np.ndim(grid) == 0 or len(grid) == 1:
        g0 = int(np.asarray(grid).ravel()[0])
        grid = (g0, g0)
    x = grid1(int(grid[0]), xlim, edge=True)
    y = grid1(int(grid[1]), ylim, edge=True)
    xy = grid2(x, y)
    dens_grid, unc_grid = _densNuncer(xy, pro, mu, sigma)
    lx, ly = len(x), len(y)
    if what == "density":
        zz = dens_grid.reshape((lx, ly), order="F")
    else:
        zz = unc_grid.reshape((lx, ly), order="F")
    if transformation == "log":
        zz = np.log(zz)
    elif transformation == "sqrt":
        zz = np.sqrt(zz)

    if type == "contour":
        if levels is None:
            levels = pretty(zz, nlevels)
        log.contour(ax, x, y, zz, levels)
    elif type == "hdr":
        z_data, _ = _densNuncer(X, pro, mu, sigma)
        lev = np.concatenate([np.sort(hdrlevels(z_data, prob)), [1.1 * float(np.max(z_data))]])
        log.window(ax, (float(x.min()), float(x.max())), (float(y.min()), float(y.max())))
        palette = _default_hdr_palette if hdr_palette is None else hdr_palette
        log.filled_contour(ax, x, y, zz, lev, palette(len(lev)))
    elif type == "image":
        palette = _default_col_palette if col_palette is None else col_palette
        colors = list(palette(nlevels))
        if len(colors) == 1:
            if levels is not None:
                nlevels = len(levels)
            alphas = r_seq_len(0.1, 1.0, nlevels)
            colors = [adjustcolor(colors[0], float(a)) for a in alphas]
        log.image(ax, x, y, zz, colors)
    elif type == "persp":
        # R's persp receives a matrix with x varying by row and y by
        # column.  Matplotlib's surface mesh uses the same orientation
        # when indexing="ij".
        if ax is not None and not hasattr(ax, "plot_surface"):
            ax = ax.figure.add_subplot(111, projection="3d")
        if ax is not None:
            xx, yy = np.meshgrid(x, y, indexing="ij")
            color = adjustcolor(col, 0.5)
            ax.plot_surface(
                xx, yy, zz, color=color, edgecolor="none",
                antialiased=True, shade=True,
            )
            theta = -30.0
            phi = 20.0
            ax.view_init(elev=phi, azim=theta)
            # The R implementation overlays profile lines at the interior
            # indices selected by floor(seq(..., length.out=2*nlevels)).
            iy = np.floor(np.linspace(1, len(y), 2 * nlevels)).astype(int)
            for i in iy[1:-1]:
                ax.plot(x, np.full_like(x, y[i - 1]), zz[:, i - 1],
                        color=col, alpha=0.5)
            ix = np.floor(np.linspace(1, len(x), 2 * nlevels)).astype(int)
            for i in ix[1:-1]:
                ax.plot(np.full_like(y, x[i - 1]), y, zz[i - 1, :],
                        color=col, alpha=0.5)
    return {"x": x, "y": y, "z": zz}
