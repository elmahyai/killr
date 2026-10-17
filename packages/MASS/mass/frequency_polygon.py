"""Frequency polygon (MASS frequency.polygon).

R computes ``hist(x, nclass, probability = TRUE, plot = FALSE)``, takes the
midpoints of the classes, and plots the counts against them as a line. The
data part is ``frequency_polygon_data``. The drawing is one Matplotlib line,
so it is called directly and is not a killplot function.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from mass.hist_fd import _extend, r_hist
from mass.misc import nclass_freq


def frequency_polygon_data(x, nclass: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Midpoints and counts that R's ``frequency.polygon`` plots."""
    values = np.asarray(x, dtype=float).reshape(-1)
    values = values[np.isfinite(values)]
    if nclass is None:
        nclass = nclass_freq(values)
    hst = r_hist(values, nclass)
    breaks = hst["breaks"]
    midpoints = 0.5 * (breaks[:-1] + breaks[1:])
    return midpoints, hst["counts"]


def frequency_polygon(
    x,
    nclass: int | None = None,
    xlab: str = "",
    ylab: str = "",
    ax=None,
    plot: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Plot the frequency polygon of ``x`` and return what was drawn."""
    midpoints, counts = frequency_polygon_data(x, nclass)
    result: dict[str, Any] = {"midpoints": midpoints, "counts": counts}
    if not plot:
        return result
    import matplotlib.pyplot as plt

    created = ax is None
    if created:
        _, ax = plt.subplots()
    ax.plot(midpoints, counts, color=kwargs.pop("col", "black"), linestyle="-")
    xlim = _extend(float(midpoints.min()), float(midpoints.max()))
    ylim = _extend(float(counts.min()), float(counts.max()))
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    if created:
        ax.figure.tight_layout()
    result.update({"xlim": xlim, "ylim": ylim, "axes": ax})
    return result
