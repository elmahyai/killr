"""The Runge function."""

from __future__ import annotations

import numpy as np


def runge(x):
    values = np.asarray(x, dtype=float)
    return 1.0 / (1.0 + (5.0 * values) ** 2)
