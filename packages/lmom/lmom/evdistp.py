from __future__ import annotations

import numpy as np


def evdistp(pfunc, para, npoints=101, **kwargs):
    """Return reduced variates and CDF curve data for an extreme-value plot."""
    f = np.linspace(1.0 / (npoints + 1), npoints / (npoints + 1), int(npoints))
    y = np.asarray(pfunc(f, para, **kwargs), dtype=float)
    return -np.log(-np.log(f)), y
