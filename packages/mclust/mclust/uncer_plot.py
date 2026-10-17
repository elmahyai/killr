"""uncerPlot: uncertainty in the order of increasing uncertainty (mclust graphics.R)."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .class_error import classError
from .map_util import map as r_map
from .plot_log import PlotLog, class_levels

__all__ = ["uncerPlot"]


def uncerPlot(
    z: Any,
    truth: Sequence[Any] | None = None,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """Plot the uncertainty of each observation in increasing order.

    Misclassified observations, when ``truth`` is given, get a vertical line
    from the baseline up to their uncertainty.
    """
    if log is None:
        log = PlotLog()
    zz = np.asarray(z, dtype=float)
    uncer = 1.0 - zz.max(axis=1)
    n = uncer.size
    order = np.argsort(uncer, kind="stable")
    M = float(uncer.max())
    xs = np.arange(1, n + 1, dtype=float)
    yv = uncer[order]
    usr = log.window(ax, (1.0, float(n)), (-(M / 32.0), M))
    log.points(ax, xs, yv, 15, "black")
    log.lines(ax, xs, yv)
    for h in (0.0, 0.0):
        log.lines(ax, [usr[0], usr[1]], [h, h])
    if truth is not None:
        codes = _factor_codes(truth)
        result = r_map(zz, warn=False)
        bad = np.asarray(classError(result.tolist(), codes.tolist())["misclassified"],
                         dtype=float)
        for i in bad.astype(int):
            p = int(np.flatnonzero(order == i - 1)[0]) + 1
            log.lines(ax, [float(p), float(p)], [-(0.5 / 32.0), float(uncer[i - 1])])


def _factor_codes(values: Sequence[Any]) -> np.ndarray:
    """``as.numeric(as.factor(values))``: 1-based codes of the sorted levels."""
    chars, levels = class_levels(values)
    index = {lev: k + 1 for k, lev in enumerate(levels)}
    return np.array([index[c] for c in chars], dtype=float)

