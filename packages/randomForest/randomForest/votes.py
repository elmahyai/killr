"""Vote margins, median fill, and the outlier score from randomForest.

The median is NumPy's, which matches R's default median on these checks.
The outlier scale is R's mad constant 1.4826.
"""

from __future__ import annotations

import numpy as np

_MAD = 1.4826


def na_roughfix(values):
    """Replace each missing entry with the median of its column."""
    data = np.asarray(values, dtype=float)
    if data.ndim == 1:
        if not np.isnan(data).any():
            return [float(item) for item in data]
        filled = data.copy()
        filled[np.isnan(filled)] = np.nanmedian(data)
        return [float(item) for item in filled]
    if data.ndim != 2:
        raise ValueError("can't handle objects with more than two dimensions")
    filled = data.copy()
    for column in range(filled.shape[1]):
        missing = np.isnan(filled[:, column])
        if missing.any():
            filled[missing, column] = np.nanmedian(filled[:, column])
    return filled.tolist()


def margin(votes, observed):
    """Vote share of the observed class, minus the next largest share."""
    table = np.asarray(votes, dtype=float)
    labels = [str(item) for item in observed]
    levels = []
    for label in labels:
        if label not in levels:
            levels.append(label)
    if table.ndim != 2 or table.shape[1] != len(levels):
        raise ValueError("number of columns in x must equal the number of levels in observed")
    if np.any(table > 1):
        totals = table.sum(axis=1, keepdims=True)
        table = table / totals
    out = []
    for row, label in enumerate(labels):
        column = levels.index(label)
        others = [table[row, index] for index in range(table.shape[1]) if index != column]
        out.append(float(table[row, column] - max(others)))
    return out


def outlier(proximity, cls=None):
    """Outlier score from a square proximity matrix."""
    data = np.asarray(proximity, dtype=float)
    if data.ndim != 2 or data.shape[0] != data.shape[1]:
        raise ValueError("x must be a square matrix")
    n = data.shape[0]
    labels = [1] * n if cls is None else [str(item) for item in cls]
    if len(labels) != n:
        raise ValueError("cls must have one label per row")
    levels = []
    for label in labels:
        if label not in levels:
            levels.append(label)
    scores = [float("nan")] * n
    for level in levels:
        chosen = [index for index, label in enumerate(labels) if label == level]
        block = data[np.ix_(chosen, chosen)]
        raw = np.sum(block * block, axis=1)
        raw = n / np.where(raw == 0, 1, raw)
        center = np.median(raw)
        scale = _MAD * np.median(np.abs(raw - center))
        adjusted = (raw - center) / scale
        for index, value in zip(chosen, adjusted):
            scores[index] = float(value)
    return scores
