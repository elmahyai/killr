"""Overview of the plotting symbols: Python translation of R's pchlist (ca 0.72).

R draws pch 1:256 on a 16 x 16 grid with rep(1:16, each = 16) for x and
rep(1:16, 16) for y, with no axes and a box. ``pchlist_data`` computes those
points and the axis limits. ``pchlist`` draws them.
"""

import numpy as np
import matplotlib.pyplot as plt

from ._rgraphics import PDF_PIN, r_extend
from ._symbols import draw_points


def pchlist_data(pin=PDF_PIN):
    """Points, symbol codes and axis limits that pchlist draws."""
    x = np.repeat(np.arange(1, 17, dtype=float), 16)
    y = np.tile(np.arange(1, 17, dtype=float), 16)
    pch = np.arange(1, 257, dtype=float)
    return {
        "x": x,
        "y": y,
        "pch": pch,
        "cex": [1.0],
        "col": ["black"],
        "xlim": r_extend(1.0, 16.0),
        "ylim": r_extend(1.0, 16.0),
    }


def pchlist(ax=None):
    """Draw the symbol overview on ``ax`` (default: the current axes)."""
    if ax is None:
        ax = plt.gca()
    data = pchlist_data()
    draw_points(ax, data["x"], data["y"], data["pch"], data["cex"], data["col"])
    ax.set_xlim(*data["xlim"])
    ax.set_ylim(*data["ylim"])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    return data
