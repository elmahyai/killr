"""randProj: random two-dimensional projections of multivariate data (mclust graphics.R).

The random basis is ``randomOrthogonalMatrix(d, 2)`` from mclust's util.R: the
Q factor of a d-by-2 matrix of normal draws. The draws use R's generator
(``boot.rng`` through ``_sim_common``), so each seed gives R's basis.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from ._sim_common import rnorm_matrix, seed_if_given
from .class_error import classError
from .map_util import map as r_map
from .mclust_2d_plot import class_symbols_colors
from .mclust_options import mclust_options
from .mvn2plot import mvn2plot
from .plot_log import PlotLog, _as_char, class_levels

__all__ = ["randProj", "random_orthogonal_matrix"]


def random_orthogonal_matrix(nrow: int, ncol: int) -> np.ndarray:
    """``qr.Q(qr(matrix(rnorm(nrow * ncol), nrow, ncol)))`` with R's random stream."""
    draws = rnorm_matrix(int(nrow), int(ncol))
    q, _ = np.linalg.qr(draws, mode="reduced")
    return q


def randProj(
    data: Any,
    seeds: Sequence[int] | None = None,
    parameters: dict | None = None,
    z: Any = None,
    classification: Sequence[Any] | None = None,
    truth: Sequence[Any] | None = None,
    uncertainty: Sequence[float] | None = None,
    what: str = "classification",
    quantiles: Sequence[float] = (0.75, 0.95),
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
) -> dict[str, Any]:
    """Project the data onto a random 2-d basis for each seed and draw the projection.

    Returns the basis, the projected data, the projected means and the
    projected covariances of the last seed, as R's invisible list does.
    """
    if log is None:
        log = PlotLog()
    X = np.asarray(data, dtype=float)
    if fillEllipses is None:
        fillEllipses = bool(mclust_options("fillEllipses"))
    if classification is None and z is not None:
        classification = r_map(np.asarray(z, dtype=float), warn=False)
    if uncertainty is None and z is not None:
        uncertainty = 1.0 - np.asarray(z, dtype=float).max(axis=1)
    d = X.shape[1]
    have_params = parameters is not None
    mu = sigma = cho = None
    G = 0
    if have_params:
        mu = np.asarray(parameters["mean"], dtype=float)
        if mu.ndim == 1:
            mu = mu.reshape(-1, 1)
        sigma = np.asarray(parameters["variance"]["sigma"], dtype=float)
        G = mu.shape[1]
        if sigma.ndim != 3 or sigma.shape[2] != G:
            have_params = False
        else:
            cho = [np.linalg.cholesky(sigma[:, :, g]).T for g in range(G)]

    truth_chr = None
    cls_chr = None
    U: list[str] = []
    L = None
    if truth is not None:
        if classification is None:
            classification = truth
            truth = None
        else:
            if len({str(v) for v in truth}) != len({str(v) for v in classification}):
                truth = None
            else:
                truth_chr = [_as_char(v) for v in truth]
    if classification is not None:
        cls_chr, U = class_levels(classification)
        L = len(U)
        symbols, colors = class_symbols_colors(U, symbols, colors)
        cls_chr = np.asarray(cls_chr, dtype=object)

    if what not in ("classification", "error", "uncertainty"):
        raise ValueError("what improperly specified")
    bad = what == "classification" and cls_chr is None
    bad = bad or (what == "uncertainty" and uncertainty is None)
    bad = bad or (what == "error" and (cls_chr is None or truth_chr is None))
    if bad:
        raise ValueError("insufficient input for specified plot")

    null_xlim = xlim is None
    null_ylim = ylim is None
    if seeds is None or len(seeds) == 0:
        raise ValueError("seeds must be given for a reproducible projection")
    result: dict[str, Any] = {}
    dd = d
    for seed in seeds:
        seed_if_given(int(seed))
        B = random_orthogonal_matrix(dd, 2)
        P = X @ B
        if null_xlim:
            xlim = (float(P[:, 0].min()), float(P[:, 0].max()))
        if null_ylim:
            ylim = (float(P[:, 1].min()), float(P[:, 1].max()))
        if scale:
            dd_new = (xlim[1] - xlim[0]) - (ylim[1] - ylim[0])
            if dd_new > 0:
                ylim = (ylim[0] - dd_new / 2, ylim[1] + dd_new / 2)
            else:
                xlim = (xlim[0] + dd_new / 2, xlim[1] - dd_new / 2)
            dd = dd_new  # R reuses the name d for this value on the next seed
        fill = fillEllipses
        if what == "classification":
            log.window(ax, xlim, ylim)
            for k in range(L):
                I = cls_chr == U[k]
                log.points(ax, P[I, 0], P[I, 1], symbols[k], colors[k])
        elif what == "error":
            errors = np.asarray(
                classError(cls_chr.tolist(), truth_chr)["misclassified"], dtype=float)
            log.window(ax, xlim, ylim)
            CLASSES = list(dict.fromkeys(truth_chr))
            sym_open = [2, 0, 1, 5]
            sym_fill = [17, 15, 16, 18]
            # R: good <- !ERRORS. ERRORS holds 1-based indices, so this is the
            # logical vector !index, which R recycles over the rows.
            good_vec = np.array([int(e) == 0 for e in errors], dtype=bool)
            n = P.shape[0]
            good = np.resize(good_vec, n) if good_vec.size else np.zeros(n, dtype=bool)
            if L > 4:
                log.points(ax, P[good, 0], P[good, 1], 1, colors)
                log.points(ax, P[~good, 0], P[~good, 1], 16)
            else:
                error_idx = set(int(e) - 1 for e in errors)
                for k in range(L):
                    K = np.array([t == CLASSES[k] for t in truth_chr], dtype=bool)
                    log.points(ax, P[K, 0], P[K, 1], sym_open[k], colors[k])
                    I = np.array([(i in error_idx) and K[i] for i in range(n)], dtype=bool)
                    if I.any():
                        log.points(ax, P[I, 0], P[I, 1], sym_fill[k])
        elif what == "uncertainty":
            unc = np.asarray(uncertainty, dtype=float)
            log.window(ax, xlim, ylim)
            breaks = np.quantile(unc, sorted(quantiles))
            I1 = unc <= breaks[0]
            log.points(ax, P[I1, 0], P[I1, 1], 16, "gray75")
            I2 = (unc <= breaks[1]) & ~I1
            log.points(ax, P[I2, 0], P[I2, 1], 16, "gray50")
            I3 = (unc > breaks[1]) & ~I2
            log.points(ax, P[I3, 0], P[I3, 1], 16, "black")
            fill = False
        else:
            log.window(ax, xlim, ylim)
            log.points(ax, P[:, 0], P[:, 1], PCH, "black")

        mu_proj = B.T @ mu if have_params else None
        sigma_proj = None
        if have_params:
            sigma_proj = np.zeros((2, 2, G))
            for g in range(G):
                M = cho[g] @ B
                sigma_proj[:, :, g] = M.T @ M
        if have_params and addEllipses:
            for g in range(G):
                col = colors[g] if fill else ["grey30"] * 3
                mvn2plot(mu_proj[:, g], sigma_proj[:, :, g], k=15, fillEllipse=fill,
                         col=col, ax=ax, log=log)
        result = {"basis": B, "data": P, "mu": mu_proj, "sigma": sigma_proj}
    return result
