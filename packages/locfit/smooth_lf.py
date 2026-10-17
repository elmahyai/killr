"""Convenience local smoothing wrapper."""

import numpy as np


def smooth_lf(x, y=None, xev=None, direct=False, **kwargs):
    if y is None:
        y = x
        x = np.arange(1, len(y) + 1, dtype=float)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if xev is None:
        xev = x
    xev = np.asarray(xev, dtype=float)
    if "fit" in kwargs:
        fitted = np.asarray(kwargs["fit"](x, y, xev=xev, direct=direct), dtype=float)
    else:
        order = int(kwargs.get("deg", 1))
        span = float(kwargs.get("alpha", kwargs.get("nn", 0.7)))
        n = len(x)
        k = max(order + 1, min(n, int(np.ceil(span * n))))
        fitted = np.empty(xev.size)
        for i, point in enumerate(xev.reshape(-1)):
            distance = np.abs(x - point)
            idx = np.argpartition(distance, k - 1)[:k]
            scale = max(distance[idx].max(), np.finfo(float).eps)
            w = np.maximum(1.0 - (distance[idx] / scale) ** 3, 0.0) ** 3
            design = np.vander(x[idx] - point, order + 1, increasing=True)
            fitted[i] = np.linalg.lstsq(design * np.sqrt(w[:, None]), y[idx] * np.sqrt(w),
                                         rcond=None)[0][0]
    if np.ndim(xev) > 1:
        fitted = fitted.reshape(xev.shape[:-1])
    return {"x": xev, "y": fitted, "call": None}
