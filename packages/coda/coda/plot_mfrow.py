"""Page layout matching coda ``set.mfrow`` with one plot per variable."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

_MFROW_ONE = {
    1: (1, 1),
    2: (1, 2),
    3: (2, 2),
    4: (2, 2),
    5: (3, 2),
    6: (3, 2),
    7: (3, 3),
    8: (3, 3),
    9: (3, 3),
    10: (3, 2),
    11: (3, 2),
    12: (3, 2),
    13: (3, 3),
}


def mfrow_one(nparms):
    """Rows and columns from ``set.mfrow(Nchains, Nparms)`` when ``nplots == 1``."""
    if nparms is None:
        key = 13
    else:
        key = min(int(nparms), 13)
        if key < 1:
            key = 13
    return _MFROW_ONE[key]


def draw_paginated(panels, nparms, draw_panel):
    """Draw ``panels`` on pages sized by ``mfrow_one(nparms)``."""
    nrows, ncols = mfrow_one(nparms)
    slots = nrows * ncols
    figures = []
    if not panels:
        return figures
    for start in range(0, len(panels), slots):
        chunk = panels[start : start + slots]
        figure, axes = plt.subplots(
            nrows,
            ncols,
            figsize=(7, max(3.0, 2.5 * nrows)),
            squeeze=False,
        )
        flat = axes.ravel()
        for axis in flat:
            axis.set_visible(False)
        for axis, panel in zip(flat, chunk):
            axis.set_visible(True)
            draw_panel(axis, panel)
        figure.tight_layout()
        figures.append(figure)
    return figures
