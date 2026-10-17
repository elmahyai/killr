"""imputePairs: pairs plot of the imputed data (mclust::imputePairs).

The panel order, the classification of rows with a missing value, the axis
limits and the label placement follow mclust's R code. The layout is
killplot.pairs_grid. Tick positions are Matplotlib's, not R's pretty() values,
so they are a rendering difference only.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextToPath

from killplot import pairs_grid

__all__ = ["impute_pairs"]

_MISSING = object()
_DEFAULT = object()
_EXPAND = 0.04  # R's xaxs = "r" and yaxs = "r" extend the range by 4 percent.


def _r_limits(values):
    """The axis limits R's plot(type = "n") gives for these values."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    lo, hi = float(v.min()), float(v.max())
    if lo == hi:
        if lo == 0.0:
            lo, hi = -1.0, 1.0
        else:
            t = 0.4 * abs(lo)
            lo, hi = lo - t, hi + t
    span = hi - lo
    return lo - _EXPAND * span, hi + _EXPAND * span


def _points(ax, x, y, pch, col):
    """R's points(): pch 1 is an open circle, pch 16 a filled circle."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    pch = np.asarray(pch, dtype=float)
    col = list(col)
    for code in np.unique(pch):
        m = pch == code
        cols = [col[k] for k in np.nonzero(m)[0]]
        if code == 1:
            ax.scatter(x[m], y[m], s=16, marker="o", facecolors="none", edgecolors=cols)
        else:
            ax.scatter(x[m], y[m], s=16, marker="o", c=cols, edgecolors="none")


def _text_label(ax, x, y, txt, cex, font):
    """R's text() centred at (x, y), with the cex and font arguments."""
    ax.text(
        x,
        y,
        txt,
        fontsize=12.0 * cex,
        fontweight="bold" if font == 2 else "normal",
        ha="center",
        va="center",
    )


def _label_cex(labels, width_inches):
    """cex.labels = max(0.8, min(2, 0.9 / max(strwidth(labels, "user"))))."""
    prop = FontProperties(size=12.0)
    widths = []
    for text in labels:
        w_pt, _, _ = TextToPath().get_text_width_height_descent(text, prop, ismath=False)
        widths.append((w_pt / 72.0) / width_inches)
    return max(0.8, min(2.0, 0.9 / max(widths)))


def _draw_frame(ax, i, j, nc, row1attop, has_lower, has_upper):
    """Box the panel and put axes on the outer edges, as R's localAxis does."""
    ax.set_axis_on()
    for spine in ax.spines.values():
        spine.set_visible(True)
    ax.tick_params(
        top=False,
        bottom=False,
        left=False,
        right=False,
        labeltop=False,
        labelbottom=False,
        labelleft=False,
        labelright=False,
    )
    i1, j1 = i + 1, j + 1
    not_both = (not has_upper) or (not has_lower)
    if i1 == 1 and (j1 % 2 == 0 or not_both):
        side = 3 if row1attop else 1  # 1 + 2 * row1attop
        _show_side(ax, side)
    if i1 == nc and (j1 % 2 == 1 or not_both):
        side = 1 if row1attop else 3  # 3 - 2 * row1attop
        _show_side(ax, side)
    if j1 == 1 and (i1 % 2 == 0 or not_both):
        _show_side(ax, 2)
    if j1 == nc and (i1 % 2 == 1 or not_both):
        _show_side(ax, 4)


def _show_side(ax, side):
    """Side 1 is bottom, 2 left, 3 top, 4 right, as in R's axis()."""
    name = {1: "bottom", 2: "left", 3: "top", 4: "right"}[side]
    ax.tick_params(**{name: True, "label" + name: True})


def impute_pairs(
    data,
    data_imp,
    symbols=(1, 16),
    colors=("black", "red"),
    labels=_MISSING,
    panel=None,
    lower_panel=_DEFAULT,
    upper_panel=_DEFAULT,
    diag_panel=None,
    text_panel=None,
    label_pos=None,
    cex_labels=None,
    font_labels=1,
    row1attop=True,
    gap=0.2,
    main=None,
    fig=None,
):
    """Draw the scatterplot matrix of the imputed data.

    ``data`` holds the observed values with NaN for the missing ones. A row with
    a missing value in columns i and j is drawn with ``symbols[2]`` and
    ``colors[2]``, and the other rows with the first entry. ``data_imp`` is the
    completed data that is plotted. ``labels`` is the diagonal text; ``None``
    means no labels. A panel callable receives ``(ax, x, y, pch, col)``.
    ``lower_panel=None`` leaves the lower triangle empty, and the same holds for
    ``upper_panel``.
    """
    obs = np.asarray(data, dtype=float)
    imp = np.asarray(data_imp, dtype=float)
    if obs.ndim != 2 or obs.shape != imp.shape:
        raise ValueError("data and data_imp must be matrices of the same shape")
    nc = obs.shape[1]
    if nc < 2:
        raise ValueError("only one column in the argument to 'pairs'")

    panel = _points if panel is None else panel
    lower = panel if lower_panel is _DEFAULT else lower_panel
    upper = panel if upper_panel is _DEFAULT else upper_panel
    diag = diag_panel
    text = _text_label if text_panel is None else text_panel
    has_lower = lower is not None
    has_upper = upper is not None
    has_diag = diag is not None
    if row1attop:
        lower, upper = upper, lower
        has_lower, has_upper = has_upper, has_lower

    has_labs = True
    if labels is _MISSING:
        labels = [f"var {k + 1}" for k in range(nc)]
    elif labels is None:
        has_labs = False
    if label_pos is None:
        label_pos = 0.5 + (1.0 / 3.0 if has_diag else 0.0)

    if fig is None:
        fig = plt.figure(figsize=(7.0, 7.0))
    flat = [ax for row in pairs_grid(fig, nc, gap=gap) for ax in row]
    if main is not None:
        fig.suptitle(main)

    order = range(nc) if row1attop else range(nc - 1, -1, -1)
    cex = cex_labels
    k = 0
    for i in order:
        for j in range(nc):
            ax = flat[k]
            k += 1
            x_j = imp[:, j]
            y_i = imp[:, i]
            ax.set_xlim(_r_limits(x_j))
            ax.set_ylim(_r_limits(y_i))
            if not (i == j or (i < j and has_lower) or (i > j and has_upper)):
                ax.set_axis_off()
                continue
            _draw_frame(ax, i, j, nc, row1attop, has_lower, has_upper)
            if i == j:
                if has_diag:
                    diag(ax, imp[:, i])
                if has_labs:
                    ax.set_xlim(0.0, 1.0)
                    ax.set_ylim(0.0, 1.0)
                    if cex is None:
                        width = ax.get_position().width * fig.get_size_inches()[0]
                        cex = _label_cex(labels, width)
                    text(ax, 0.5, label_pos, labels[i], cex, font_labels)
                continue
            cls = np.where(np.isnan(obs[:, [i, j]]).any(axis=1), 2, 1)
            pch = [symbols[c - 1] for c in cls]
            col = [colors[c - 1] for c in cls]
            if i < j:
                lower(ax, x_j, y_i, pch, col)
            else:
                upper(ax, x_j, y_i, pch, col)
    return None
