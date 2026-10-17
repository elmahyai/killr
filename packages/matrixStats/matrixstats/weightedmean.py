"""Weighted arithmetic mean, ported from matrixStats ``weightedMean``."""

from __future__ import annotations

import numpy as np
from weightedmean import weighted_mean as _weighted_mean


def weightedMean(x, w=None, idxs=None, na_rm=False, refine=False) -> float:
    """Weighted arithmetic mean of a numeric vector.

    Mirrors ``matrixStats::weightedMean``. ``idxs`` is 1-based. ``None`` uses
    every element. ``w`` of ``None`` gives every element the same weight.
    A weight of zero is skipped. A missing weight makes the result missing
    when the paired ``x`` value is present, whether or not ``na_rm`` is set.
    ``na_rm`` skips points whose ``x`` is missing. ``refine`` defaults to
    false and, when true, corrects the mean with a second pass over residuals.
    An empty input returns NaN.
    """
    values = np.ascontiguousarray(np.asarray(x, dtype=np.float64))
    if values.ndim != 1:
        raise ValueError("Argument 'x' must be a vector")
    if w is None:
        weights = None
    else:
        weights = np.ascontiguousarray(np.asarray(w, dtype=np.float64))
        if weights.ndim != 1:
            raise ValueError("Argument 'w' must be a vector")
    return float(
        _weighted_mean(values, weights, _as_index(idxs), bool(na_rm), bool(refine))
    )


def _as_index(idxs):
    if idxs is None:
        return None
    index = np.asarray(idxs)
    if index.ndim == 0:
        index = index.reshape(1)
    if index.ndim != 1:
        raise ValueError("Argument 'idxs' must be a vector")
    if index.dtype == np.bool_:
        return np.ascontiguousarray(index)
    if index.dtype == np.int32:
        return np.ascontiguousarray(index)
    if np.issubdtype(index.dtype, np.integer):
        return np.ascontiguousarray(index, dtype=np.int64)
    if np.issubdtype(index.dtype, np.floating):
        return np.ascontiguousarray(index, dtype=np.float64)
    raise ValueError("idxs can only be integer, numeric, or logical")
