"""Shared helpers for the locfit Python translations."""

from __future__ import annotations

import numpy as np


def design(x: np.ndarray, degree: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    cols = [np.ones(len(x))]
    if degree >= 1:
        cols.extend(x[:, j] for j in range(x.shape[1]))
    if degree >= 2:
        cols.extend(x[:, j] * x[:, k] for j in range(x.shape[1]) for k in range(j, x.shape[1]))
    return np.column_stack(cols)


def fit_local(x, y, xev=None, alpha=0.7, deg=2, weights=None, robust=None):
    """Small, dependency-free local polynomial fit used by all wrappers."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    y = np.asarray(y, dtype=float).reshape(-1)
    if len(x) != len(y):
        raise ValueError("x and y must have the same number of rows")
    points = x if xev is None else np.atleast_2d(np.asarray(xev, dtype=float))
    if points.shape[1] != x.shape[1]:
        raise ValueError("evaluation points have the wrong dimension")
    base_w = np.ones(len(y)) if weights is None else np.asarray(weights, dtype=float)
    if len(base_w) != len(y):
        raise ValueError("weights must have length len(y)")
    p = design(np.zeros((1, x.shape[1])), deg).shape[1]
    coef = np.empty((len(points), p))
    fitted = np.empty(len(points))
    bandwidth = np.empty(len(points))
    for i, point in enumerate(points):
        distance = np.sqrt(np.sum((x - point) ** 2, axis=1))
        positive = distance[distance > 0]
        h = np.quantile(positive, min(max(float(alpha), 1e-6), 1.0)) if len(positive) else 1.0
        h = max(float(h), np.finfo(float).eps)
        u = distance / h
        kernel = np.where(u < 1, (1 - u**3) ** 3, 0.0)
        w = kernel * base_w
        if robust is not None:
            w *= np.asarray(robust, dtype=float)
        z = x - point
        a = design(z, deg)
        sw = np.sqrt(np.maximum(w, 0))
        aw = a * sw[:, None]
        yw = y * sw
        beta = np.linalg.lstsq(aw, yw, rcond=None)[0]
        coef[i] = beta
        fitted[i] = beta[0]
        bandwidth[i] = h
    return {"coef": coef, "fit": fitted, "h": bandwidth, "xev": points}


def unwrap_data(x, y=None):
    if y is not None:
        return x, y
    if isinstance(x, dict):
        return x["x"], x["y"]
    raise ValueError("y is required unless x is a mapping with x and y")
