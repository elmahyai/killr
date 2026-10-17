"""Hampel filter for isolated outliers."""

from __future__ import annotations

import numpy as np

from pracma.num_helpers import r_median


def hampel(x, k, t0=3):
    series = np.asarray(x, dtype=float).reshape(-1)
    corrected = series.copy()
    indices = []
    scale = 1.4826
    half = int(k)
    for i in range(half, series.size - half):
        window = series[i - half:i + half + 1]
        center = r_median(window)
        deviation = scale * r_median(np.abs(window - center))
        if abs(series[i] - center) > t0 * deviation:
            corrected[i] = center
            indices.append(i + 1)
    return {"y": corrected, "ind": None if not indices else np.array(indices, dtype=float)}
