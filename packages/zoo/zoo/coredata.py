"""Core data of a zoo series.

``coredata`` returns the observations and leaves the index behind.
``coredata<-`` writes new observations into the existing shape. The
R method does not call ``zoo_coredata``; that ``.Call`` is commented out.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from zoo.series import Zoo


def coredata(x: Any, **kwargs: Any) -> Any:
    """Extract the observations. A zoo series returns its data array."""
    del kwargs
    if isinstance(x, Zoo):
        return np.array(x.data, copy=True, order="F")
    if getattr(x, "tsp", None) is not None and not isinstance(x, Zoo):
        data = getattr(x, "data", x)
        return np.array(data, copy=True, order="F")
    return coredata_default(x)


def coredata_default(x: Any, **kwargs: Any) -> Any:
    """``coredata.default`` returns ``x`` unchanged."""
    del kwargs
    return x


def coredata_set(x: Any, value: Any) -> Any:
    """Replace the observations. The index and its length stay as they are."""
    if isinstance(x, Zoo):
        return _set_zoo(x, value)
    raise ValueError("no applicable method for 'coredata<-'")


def _set_zoo(x: Zoo, value: Any) -> Zoo:
    if _length(x) != _length(value):
        raise ValueError("length(x) == length(value) is not TRUE")
    if not (_is_vector(value) or _is_factor(value) or _is_matrix(value) or _is_data_frame(value)):
        raise ValueError("“value” : attempt to assign invalid coredata to zoo object")
    incoming = value
    if _is_matrix(value) or _is_data_frame(value):
        incoming = _as_matrix(value)
    data = _assign(x.data, incoming)
    index = np.array(x.index, copy=True) if isinstance(x.index, np.ndarray) else (
        list(x.index) if isinstance(x.index, (list, tuple)) else x.index
    )
    return Zoo(data, index, frequency=x.frequency, regular=x.regular)


def _assign(data: Any, value: Any) -> np.ndarray:
    incoming = np.array(value, order="F", copy=True)
    flat = np.ravel(incoming, order="F")
    out = np.array(data, copy=True, order="F")
    if flat.dtype.kind == "f" and out.dtype.kind in "iu":
        out = out.astype(float)
    target = np.ravel(out, order="F")
    if flat.size != target.size:
        if flat.size == 0:
            raise ValueError("replacement has length zero")
        flat = flat[np.arange(target.size) % flat.size]
    target[...] = flat
    return out


def _length(value: Any) -> int:
    if isinstance(value, Zoo):
        return int(np.size(value.data))
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, np.ndarray):
        return int(value.size)
    if isinstance(value, str):
        return 1
    if isinstance(value, (list, tuple, range)):
        return len(value)
    if isinstance(value, (int, float, bool, np.number)) or value is None:
        return 1
    try:
        return len(value)
    except TypeError:
        return 1


def _is_vector(value: Any) -> bool:
    if isinstance(value, np.ndarray):
        return value.ndim <= 1
    if isinstance(value, dict):
        return False
    if isinstance(value, (list, tuple, range, str)):
        return True
    if isinstance(value, (int, float, bool, np.number)) or value is None:
        return True
    return False


def _is_matrix(value: Any) -> bool:
    return isinstance(value, np.ndarray) and value.ndim == 2


def _is_data_frame(value: Any) -> bool:
    return isinstance(value, dict)


def _is_factor(value: Any) -> bool:
    return getattr(value, "levels", None) is not None and not isinstance(value, (list, tuple, np.ndarray, dict))


def _as_matrix(value: Any) -> np.ndarray:
    if isinstance(value, dict):
        columns = [np.asarray(column) for column in value.values()]
        if not columns:
            return np.array([], dtype=float).reshape(0, 0)
        return np.column_stack(columns)
    return np.array(value, order="F", copy=True)
