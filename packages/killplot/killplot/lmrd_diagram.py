"""L-moment ratio diagram (lmom::lmrd). Matplotlib has no such chart.

The caller works out everything that depends on R's arithmetic: the curve
data, the plot-region limits, which two-parameter points lie inside the
region, and the legend anchor. This function draws those in Matplotlib.
Each curve, the two-parameter points, and the legend are one artist with a
label, so a caller can check what was drawn.
"""

from __future__ import annotations

from matplotlib.lines import Line2D
from matplotlib.transforms import ScaledTranslation

__all__ = ["lmrd_diagram"]


def lmrd_diagram(ax, xlim, ylim, curves, twopar, legend=None, xlabel="", ylabel="",
                 frame_color="black"):
    """Draw an L-moment ratio diagram on ``ax``.

    ``xlim`` and ``ylim`` are the plot-region limits, already extended as R does.
    ``curves`` is a list of dicts with keys ``name``, ``x``, ``y``, ``col``,
    ``linestyle`` and ``lwd``; each is one three-parameter distribution.
    ``twopar`` is a dict with ``x``, ``y`` and ``labels``: the two-parameter
    points inside the region. ``legend`` is None or a dict with ``x``, ``y``
    (top-left corner, in data units), ``labels``, ``col``, ``linestyle`` and ``lwd``.
    """
    ax.set_xlim(xlim[0], xlim[1])
    ax.set_ylim(ylim[0], ylim[1])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    for curve in curves:
        ax.plot(curve["x"], curve["y"], color=curve["col"], linestyle=curve["linestyle"],
                linewidth=curve["lwd"], label=f"curve:{curve['name']}")

    # abline(h = 0, v = 0): the zero lines through the origin.
    ax.axhline(0, color=frame_color, linewidth=0.8, label="zero_h")
    ax.axvline(0, color=frame_color, linewidth=0.8, label="zero_v")

    if len(twopar["labels"]):
        ax.plot(twopar["x"], twopar["y"], linestyle="none", marker="s", color="black",
                markerfacecolor="black", label="twopar")
        # adj = c(-0.5, -0.25) in R moves the label up and to the right of the point.
        # Matplotlib has no adj, so the label is set at a fixed offset of 3 and 2 points.
        offset = ScaledTranslation(3 / 72, 2 / 72, ax.figure.dpi_scale_trans)
        for x, y, label in zip(twopar["x"], twopar["y"], twopar["labels"]):
            ax.text(x, y, label, transform=ax.transData + offset, ha="left", va="bottom",
                    clip_on=False).set_label("twopar_text")

    if legend is not None:
        handles = [
            Line2D([0], [0], color=c, linestyle=ls, linewidth=lw)
            for c, ls, lw in zip(legend["col"], legend["linestyle"], legend["lwd"])
        ]
        ax.legend(handles, legend["labels"], loc="upper left",
                  bbox_to_anchor=(legend["x"], legend["y"]), bbox_transform=ax.transData,
                  frameon=False, borderaxespad=0.0)
    return ax
