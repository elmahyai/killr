"""Fast sum over a subset of vector elements, ported from matrixStats."""

from __future__ import annotations

import math
import warnings

import sum2 as _sum2

from matrixstats._values import as_logical, prepare_idxs, prepare_x

_R_INT_MAX = 2147483647.0
_R_INT_MIN = -2147483647.0
_DOUBLE_MODE_WARNING = (
    'sum2(x, mode = "integer") called with typeof(x) == "double"; '
    "did you mean to use as.integer(sum2(x))?"
)
_OVERFLOW_WARNING = 'Integer overflow. Use sum2(..., mode = "double") to avoid this.'


def sum2(x, idxs=None, na_rm=False, mode=None):
    """Sum all or a subset of values.

    Mirrors ``matrixStats::sum2``. ``idxs`` is 1-based, as in R. ``None``
    selects every element. A logical ``x`` defaults to an integer sum.
    Double missing values are ``nan``. An integer missing result is ``None``.
    An empty sum is 0.
    """
    na_rm = as_logical(na_rm, "na.rm")
    storage, values = prepare_x(x)
    resolved = _resolve_mode(storage, mode)
    if resolved == "integer" and storage == "double":
        warnings.warn(_DOUBLE_MODE_WARNING, UserWarning, stacklevel=2)

    idxs_kind, idxs_values = prepare_idxs(idxs)
    x_kind = "double" if storage == "double" else "integer"
    total = _sum2.sum2(values, x_kind, na_rm, idxs_values, idxs_kind)
    if resolved == "double":
        return float(total)
    if math.isnan(total):
        return None
    if total > _R_INT_MAX or total < _R_INT_MIN:
        warnings.warn(_OVERFLOW_WARNING, UserWarning, stacklevel=2)
        return None
    return int(total)


def _resolve_mode(storage: str, mode) -> str:
    if mode is None:
        return "integer" if storage in ("integer", "logical") else "double"
    if isinstance(mode, (list, tuple)):
        if not mode:
            raise ValueError("Unknown value of argument 'mode': ")
        mode = mode[0]
    if not isinstance(mode, str):
        raise ValueError(f"Unknown value of argument 'mode': {mode}")
    if storage == "logical" and mode == "logical":
        return "integer"
    if mode in ("integer", "double"):
        return mode
    raise ValueError(f"Unknown value of argument 'mode': {mode}")
