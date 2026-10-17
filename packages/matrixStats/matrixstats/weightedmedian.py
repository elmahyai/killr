"""Weighted median, ported from matrixStats ``weightedMedian``."""

from __future__ import annotations

import numpy as np
from weightedmedian import weighted_median as _weighted_median

_TIES = {"weighted": 1, "min": 2, "max": 4, "mean": 8}


def weightedMedian(x, w=None, idxs=None, na_rm=False, interpolate=None, ties=None) -> float:
    """Weighted median of a numeric vector.

    Mirrors ``matrixStats::weightedMedian``. ``idxs`` is 1-based. ``None``
    uses every element. ``w`` of ``None`` gives every element the same weight.
    A weight of zero or less is dropped. ``interpolate`` defaults to true when
    ``ties`` is omitted, and to false when ``ties`` is given.
    """
    if ties is None:
        ties_id = 1
    else:
        try:
            ties_id = _TIES[ties]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Unknown value of argument 'ties': {ties}") from exc
    if interpolate is None:
        interpolate = ties is None
    elif not isinstance(interpolate, (bool, np.bool_)):
        raise ValueError("Argument 'interpolate' must be either TRUE or FALSE")

    values = np.asarray(x, dtype=np.float64)
    if values.ndim == 0:
        values = values.reshape(1)
    values = np.ascontiguousarray(values)
    if values.ndim != 1:
        raise ValueError("Argument 'x' must be a vector")
    if w is None:
        weights = None
    else:
        weights = np.asarray(w, dtype=np.float64)
        if weights.ndim == 0:
            weights = weights.reshape(1)
        weights = np.ascontiguousarray(weights)
        if weights.ndim != 1:
            raise ValueError("Argument 'w' must be a vector")
    return float(
        _weighted_median(
            values,
            weights,
            _as_index(idxs),
            bool(na_rm),
            bool(interpolate),
            ties_id,
        )
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
