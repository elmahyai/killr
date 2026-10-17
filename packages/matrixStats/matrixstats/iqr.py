"""Interquartile range of a vector, ported from matrixStats ``iqr``."""

from __future__ import annotations

import numpy as np

from matrixstats.rowquantiles import (
    _NA_INTEGER,
    _as_flag,
    _require_type,
    _type_number,
    quantile_vector,
    resolve_index,
)

__all__ = ["iqr"]

_PROBS = np.array([0.25, 0.75], dtype=np.float64)


def iqr(x, idxs=None, na_rm=False, type=7, fuzz=None):
    """Interquartile range of a vector.

    Mirrors ``matrixStats::iqr``. ``idxs`` is 1-based. ``None`` uses every
    element. A matrix is read in column-major order, matching R. A missing
    value makes the result ``nan`` when ``na_rm`` is false. An empty vector
    is ``nan``. A single value is ``0``. The range is
    ``stats::quantile`` at 0.75 minus the quantile at 0.25.
    """
    values = _as_vector(x)
    if idxs is not None:
        chosen = []
        for position in resolve_index(idxs, values.size, "idxs"):
            chosen.append(np.nan if position is None else values[position])
        values = np.asarray(chosen, dtype=np.float64)
    if _as_flag(na_rm, "na.rm"):
        values = values[~np.isnan(values)]
    elif values.size and np.isnan(values).any():
        return float("nan")
    n = int(values.size)
    if n == 0:
        return float("nan")
    if n == 1:
        return 0.0
    choice = _require_type(_type_number(type))
    quantiles = quantile_vector(values, _PROBS, type=choice, fuzz=fuzz)
    return float(quantiles[1] - quantiles[0])


def _as_vector(x):
    if isinstance(x, (bool, np.bool_)):
        return np.array([1.0 if x else 0.0], dtype=np.float64)
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return _integers_to_float(np.array([int(x)], dtype=np.int64))
    if isinstance(x, (float, np.floating)):
        return np.array([float(x)], dtype=np.float64)
    array = np.asarray(x)
    if array.ndim == 0:
        array = array.reshape(1)
    elif array.ndim > 1:
        array = np.ravel(array, order="F")
    else:
        array = np.ravel(array)
    if array.dtype == np.bool_:
        return array.astype(np.float64)
    if np.issubdtype(array.dtype, np.integer):
        return _integers_to_float(array)
    if np.issubdtype(array.dtype, np.floating):
        return np.asarray(array, dtype=np.float64)
    raise ValueError("Argument 'x' must be logical, integer, or numeric")


def _integers_to_float(array):
    wide = np.asarray(array, dtype=np.int64)
    out = wide.astype(np.float64)
    out[wide == int(_NA_INTEGER)] = np.nan
    return out
