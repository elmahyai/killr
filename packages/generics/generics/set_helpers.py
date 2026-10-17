"""Ordered set helpers matching R's vector set operations."""

from __future__ import annotations

import math
from collections.abc import Iterable


def _values(value):
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        return [value]
    if hasattr(value, "ndim") and getattr(value, "ndim", 1) != 1:
        return list(value.reshape(-1))
    return list(value)


def _key(value):
    # R treats NA and NaN as different values for these operations, while
    # repeated instances of either value compare equal.
    if value is None:
        return ("na",)
    if isinstance(value, float) and math.isnan(value):
        return ("nan",)
    if isinstance(value, complex) and (
        math.isnan(value.real) or math.isnan(value.imag)
    ):
        return ("complex", value.real, value.imag)
    if isinstance(value, bool):
        return ("logical", value)
    if isinstance(value, (int, float, complex)):
        return ("number", value)
    try:
        hash(value)
    except TypeError:
        return ("object", repr(value))
    return (type(value), value)


def _unique(values):
    result = []
    seen = set()
    for value in values:
        key = _key(value)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def is_element(el, set):
    """Return whether each element of ``el`` occurs in ``set``."""
    keys = {_key(value) for value in _values(set)}
    return [_key(value) in keys for value in _values(el)]


def setdiff(x, y):
    """Return unique values in ``x`` that do not occur in ``y``."""
    y_keys = {_key(value) for value in _values(y)}
    return _unique(value for value in _values(x) if _key(value) not in y_keys)


def setequal(x, y):
    """Return whether ``x`` and ``y`` contain the same unique values."""
    return {_key(value) for value in _values(x)} == {
        _key(value) for value in _values(y)
    }


def union(x, y):
    """Return the ordered union of ``x`` and ``y`` without duplicates."""
    return _unique([*_values(x), *_values(y)])
