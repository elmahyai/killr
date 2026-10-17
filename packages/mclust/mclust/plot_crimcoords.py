"""Translation of ``plot.crimcoords`` (mclust 6.1.3).

With two or more directions the plot is ``clPairs`` on the projection. With
one direction it is a histogram per class on shared breaks, from
``pretty(projection, nclass.Sturges(projection))``. The drawn data go to a
``Canvas`` log, which the proof compares with R's ``trace()`` log.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from mclust._plot_common import (
    Canvas,
    cl_pairs,
    extendrange,
    hist_density,
    nclass_sturges,
    pretty,
)

__all__ = ["plot_crimcoords"]


def plot_crimcoords(x: Any, fig: Any = None, canvas: Canvas | None = None) -> Canvas:
    """Draw a ``crimcoords`` object. Returns the canvas with the drawing log."""
    canvas = canvas or Canvas()
    projection = np.asarray(x["projection"], dtype=float)
    if projection.ndim == 1:
        projection = projection.reshape(-1, 1)
    labels = np.asarray(x["classification"]).astype(str)
    numdir = projection.shape[1]

    if numdir >= 2:
        cl_pairs(canvas, fig, projection, labels)
        return canvas

    levels = sorted(set(labels.tolist()))
    values_all = projection[:, 0]
    breaks = pretty(values_all, nclass_sturges(projection))
    ax = fig.add_subplot(111) if fig is not None else None
    xlim = extendrange(breaks)
    for k, level in enumerate(levels):
        vals = projection[labels == level, 0]
        dens = hist_density(vals, breaks)["density"]
        canvas.hist(ax, breaks, dens, xlim=xlim, add=k > 0)
    return canvas
