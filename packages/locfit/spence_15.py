"""Spence's 15-point smoother."""

import numpy as np


def spence_15(y):
    y = np.asarray(y, dtype=float).reshape(-1)
    if y.size == 0:
        return np.array([], dtype=float)
    z = np.pad(y, (7, 7), mode="edge")
    y1 = z[2:-2] + 3.0 * (z[1:-3] + z[2:-2] + z[3:-1] - z[:-4] - z[4:])
    y2 = np.convolve(y1, np.ones(4), mode="valid")
    y3 = np.convolve(y2, np.ones(4), mode="valid")
    y4 = np.convolve(y3, np.ones(5), mode="valid")
    return y4 / 320.0
