"""Extreme-value plot (lmom::evplot.default). Matplotlib has no return-period axis.

The caller works out the plotting positions, the limits, the quantile curve and
the return-period ticks. This function draws them. Each part is one artist with
a label: ``points``, ``curve``, ``rp_axis``, ``rp_tick``, ``rp_label`` and
``rp_title``.
"""

from __future__ import annotations

import numpy as np

__all__ = ["extreme_value_plot"]

# R tick length: tcl = -0.5 lines, with a line of 0.2 inches.
_TICK_INCHES = 0.5 * 0.2
# R label gap: the tick labels sit just above the ticks.
_LABEL_GAP_INCHES = 0.05
# R title offset: mgp[1] = 3 lines of 0.2 inches above the axis.
_TITLE_INCHES = 3 * 0.2


def _inches_to_data_y(ax, inches):
    """A vertical distance in inches, converted to data units on ``ax``."""
    ylo, yhi = ax.get_ylim()
    height_in = ax.bbox.height / ax.figure.dpi
    return inches * (yhi - ylo) / height_in


def extreme_value_plot(ax, xlim, ylim, xlabel="", ylabel="", points=None,
                       point_type="p", curve=None, return_axis=None):
    """Draw an extreme-value plot on ``ax``.

    ``points`` is None or ``(x, y)``: the plotting positions, drawn with
    ``point_type`` as in R (``p``, ``l``, ``b``, ``o`` or ``n``).
    ``curve`` is None or ``(x, y)``: the quantile curve, drawn as a line.
    ``return_axis`` is None or a dict with ``tic`` (positions), ``lab``
    (labels), ``ypos`` (height of the axis line) and ``text_x`` (the centre
    of the title). The ticks point up from the axis line, as R's side 3 does.
    """
    ax.set_xlim(xlim[0], xlim[1])
    ax.set_ylim(ylim[0], ylim[1])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    if points is not None and point_type != "n":
        _draw_type(ax, points[0], points[1], point_type, label="points")

    if curve is not None:
        ax.plot(curve[0], curve[1], color="black", linestyle="-", label="curve")

    if return_axis is not None:
        tic = np.asarray(return_axis["tic"], dtype=float)
        labels = list(return_axis["lab"])
        ypos = float(return_axis["ypos"])
        if tic.size:
            ax.plot([tic.min(), tic.max()], [ypos, ypos], color="black", linewidth=0.8,
                    label="rp_axis")
        tick = _inches_to_data_y(ax, _TICK_INCHES)
        gap = _inches_to_data_y(ax, _LABEL_GAP_INCHES)
        for t, text in zip(tic, labels):
            ax.plot([t, t], [ypos, ypos + tick], color="black", linewidth=0.8, label="rp_tick")
            ax.text(t, ypos + tick + gap, text, ha="center", va="bottom").set_label("rp_label")
        title_y = ypos + _inches_to_data_y(ax, _TITLE_INCHES)
        ax.text(float(return_axis["text_x"]), title_y, "Return period",
                ha="center", va="bottom").set_label("rp_title")
    return ax


def _draw_type(ax, x, y, point_type, label):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if point_type == "p":
        ax.plot(x, y, linestyle="none", marker="o", markerfacecolor="none", color="black",
                label=label)
    elif point_type == "l":
        ax.plot(x, y, linestyle="-", color="black", label=label)
    elif point_type in ("b", "o"):
        ax.plot(x, y, linestyle="-", marker="o", markerfacecolor="none", color="black",
                label=label)
    else:
        raise NotImplementedError(f"point type {point_type!r} is not translated")
