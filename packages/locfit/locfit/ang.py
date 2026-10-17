"""Construct a one-column angle smoother specification."""

import numpy as np


def ang(x, *args, **kwargs):
    values = np.asarray(x, dtype=float)
    if values.ndim == 1:
        values = values[:, None]
    return values

