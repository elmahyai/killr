"""Parallel-coordinate plot (MASS parcoord).

Matplotlib has no parallel-coordinate chart, so it is drawn here. Each row of
``values`` is one line through the variable axes, which sit at x = 1..p. The
values are already scaled to the unit interval per column by the caller.

The axis limits are the ones R's ``matplot`` gives: x is the range of the
axis positions and y is the range of the values, each extended by 4 percent.
"""

from __future__ import annotations

from typing import Any

import numpy as np

_R_EXPAND = 0.04
_R_PALETTE = ["black", "#DF536B", "#61D04F", "#2297E6", "#28E2E5", "#CD0BBC", "#F5C710", "gray62"]
_GREY70 = "#B3B3B3"


def _r_color(value: Any) -> Any:
    if isinstance(value, (int, float, np.integer, np.floating)):
        idx = int(value)
        return _R_PALETTE[(idx - 1) % len(_R_PALETTE)] if idx > 0 else "white"
    return value


def _r_linestyle(value: Any) -> Any:
    table = {1: "-", 2: "--", 3: ":", 4: "-.", 5: "--", 6: "-."}
    if isinstance(value, (int, float, np.integer, np.floating)):
        return table.get(int(value), "-")
    return value


def _extend(lo: float, hi: float) -> tuple[float, float]:
    span = hi - lo
    return lo - _R_EXPAND * span, hi + _R_EXPAND * span


def parcoord(
    ax,
    values,
    col: Any = 1,
    lty: Any = 1,
    colnames: list[str] | None = None,
    labels_below: list[str] | None = None,
    labels_above: list[str] | None = None,
) -> dict[str, Any]:
    """Draw one line per row of ``values`` across ``p`` vertical axes.

    ``labels_below`` and ``labels_above`` are optional text for the bottom
    and top of each axis, one entry per column. The caller formats them.
    """
    mat = np.asarray(values, dtype=float)
    if mat.ndim != 2:
        raise ValueError("'values' must be a matrix")
    n_rows, p = mat.shape
    xs = np.arange(1, p + 1)
    cols = col if isinstance(col, (list, tuple, np.ndarray)) else [col]
    ltys = lty if isinstance(lty, (list, tuple, np.ndarray)) else [lty]
    for i in range(n_rows):
        ax.plot(
            xs,
            mat[i],
            color=_r_color(cols[i % len(cols)]),
            linestyle=_r_linestyle(ltys[i % len(ltys)]),
        )
    for i in range(p):
        ax.plot([i + 1, i + 1], [0.0, 1.0], color=_GREY70, linewidth=1.0, zorder=0)
    if labels_below is not None:
        for i in range(p):
            ax.annotate(
                str(labels_below[i]),
                (i + 1, 0.0),
                xytext=(0, -3),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=7,
                annotation_clip=False,
            )
    if labels_above is not None:
        for i in range(p):
            ax.annotate(
                str(labels_above[i]),
                (i + 1, 1.0),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
                annotation_clip=False,
            )
    names = colnames if colnames is not None else [str(i + 1) for i in range(p)]
    ax.set_xticks(xs, labels=list(names))
    finite = mat[np.isfinite(mat)]
    xlim = _extend(1.0, float(p))
    ylim = _extend(float(finite.min()), float(finite.max())) if finite.size else (0.0, 1.0)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_bounds(1, p)
    ax.tick_params(axis="y", left=False, labelleft=False)
    ax.set_xlabel("")
    ax.set_ylabel("")
    return {"xlim": xlim, "ylim": ylim, "axes": ax}
