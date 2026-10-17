"""errorBars: draw error bars with arrow heads (mclust util.R)."""

from __future__ import annotations

from typing import Any

from .plot_log import PlotLog

__all__ = ["errorBars"]


def errorBars(
    x: Any,
    upper: Any,
    lower: Any,
    width: float = 0.1,
    code: int = 3,
    angle: float = 90,
    horizontal: bool = False,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """Draw bars at ``x`` from ``upper`` to ``lower``, vertical unless ``horizontal``.

    R calls ``arrows(x, upper, x, lower, length = width, angle, code)``. The
    logged record is the arrow end points and ``code``, which is what the
    proof compares. ``width`` and ``angle`` set the arrow head size, which
    is drawn in device inches on R's device and is not reproduced here.
    """
    del angle, width  # arrow head size is not part of the compared record
    if log is None:
        log = PlotLog()
    if horizontal:
        log.arrows(ax, upper, x, lower, x, code=code)
    else:
        log.arrows(ax, x, upper, x, lower, code=code)
