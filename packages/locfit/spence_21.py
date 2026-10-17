"""Spence's 21-point smoother."""

import numpy as np


def spence_21(y):
    y = np.asarray(y, dtype=float).reshape(-1)
    if y.size == 0:
        return np.array([], dtype=float)
    z = np.pad(y, (10, 10), mode="edge")
    y1 = -z[:-6] + z[2:-4] + 2.0 * z[3:-3] + z[4:-2] - z[6:]
    y2 = np.convolve(y1, np.ones(7), mode="valid")
    y3 = np.convolve(y2, np.ones(5), mode="valid")
    y4 = np.convolve(y3, np.ones(5), mode="valid")
    return y4 / 350.0
