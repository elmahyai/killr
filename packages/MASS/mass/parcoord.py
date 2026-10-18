"""Parallel-coordinate plot of a matrix (MASS parcoord).

Each column is scaled to the unit interval by its own range, ignoring NA.
The scaled rows are drawn as lines through the columns by ``killplot.parcoord``.
Matplotlib has no parallel-coordinate chart, so that drawing is a killplot
function.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

try:
    from killplot.parcoord import parcoord as _kp_parcoord
except ImportError:  # the workspace killplot folder is not installed
    _root = Path(__file__).resolve().parents[3] / "packages" / "killplot"
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from killplot.parcoord import parcoord as _kp_parcoord


def _format_digits(values, digits: int = 3) -> list[str]:
    """R's ``format(values, digits = digits)`` for a short numeric vector.

    Each value needs enough significant digits, at most ``digits``. The
    shared decimal count is the largest one needed. Fixed notation is used
    unless scientific is narrower, as in R's formatReal.
    """
    vals = [float(v) for v in values]
    sig: list[int] = []
    expo: list[int] = []
    for v in vals:
        if v == 0.0:
            sig.append(1)
            expo.append(0)
            continue
        mant, e = f"{abs(v):.{digits - 1}e}".split("e")
        sig.append(max(1, len(mant.replace(".", "").rstrip("0"))))
        expo.append(int(e))
    rgt = max(max(0, s - 1 - e) for s, e in zip(sig, expo))
    left = max(max(e + 1, 1) for e in expo)
    neg = 1 if any(v < 0 for v in vals) else 0
    fixed_width = neg + left + (rgt + 1 if rgt > 0 else 0)
    mxsl = max(sig)
    sci_width = neg + (mxsl + 1 if mxsl > 1 else mxsl) + 4
    if fixed_width <= sci_width:
        texts = [f"{v:.{rgt}f}" for v in vals]
    else:
        texts = [f"{v:.{mxsl - 1}e}" for v in vals]
    width = max(len(t) for t in texts)
    return [t.rjust(width) for t in texts]


def parcoord_scale(x) -> tuple[np.ndarray, np.ndarray]:
    """Scale each column to [0, 1]. Returns the scaled matrix and the column ranges.

    The column ranges are ``rx`` in R, a 2 by p matrix with the minimum in
    the first row and the maximum in the second.
    """
    mat = np.asarray(x, dtype=float)
    if mat.ndim != 2:
        raise ValueError("'x' must be a matrix")
    with np.errstate(divide="ignore", invalid="ignore"):
        lo = np.nanmin(mat, axis=0)
        hi = np.nanmax(mat, axis=0)
        scaled = (mat - lo) / (hi - lo)
    return scaled, np.vstack([lo, hi])


def parcoord(
    x,
    col: Any = 1,
    lty: Any = 1,
    var_label: bool = False,
    colnames: list[str] | None = None,
    ax=None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Plot the rows of ``x`` as lines across its columns, one axis per column."""
    import matplotlib.pyplot as plt

    scaled, rx = parcoord_scale(x)
    labels_below = labels_above = None
    if var_label:
        labels_below, labels_above = [], []
        for i in range(scaled.shape[1]):
            text = _format_digits([rx[0, i], rx[1, i]], digits=3)
            labels_below.append(text[0].strip())
            labels_above.append(text[1].strip())
    created = ax is None
    if created:
        _, ax = plt.subplots()
    drawn = _kp_parcoord(
        ax,
        scaled,
        col=col,
        lty=lty,
        colnames=colnames,
        labels_below=labels_below,
        labels_above=labels_above,
    )
    if created:
        ax.figure.tight_layout()
    return {
        "scaled": scaled,
        "range": rx,
        "xlim": drawn["xlim"],
        "ylim": drawn["ylim"],
        "axes": ax,
        "labels_below": labels_below,
        "labels_above": labels_above,
    }
