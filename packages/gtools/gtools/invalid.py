"""Test missing, empty, all-NA, or try-error values (gtools 3.9.5 ``invalid``)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np

from gtools.na_replace import NA, _missing_mask

_UNSET = object()


class TryError(Exception):
    """Stand-in for R's ``try-error`` class."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


def _length(value) -> int:
    if isinstance(value, np.ndarray):
        return int(value.size)
    if isinstance(value, (str, bytes, bytearray)):
        return len(value)
    if isinstance(value, Mapping):
        return len(value)
    if isinstance(value, Sequence):
        return len(value)
    return 1


def _is_r_list(value) -> bool:
    return isinstance(value, (list, dict))


def _is_r_vector(value) -> bool:
    if isinstance(value, np.ndarray):
        return value.ndim == 1
    if _is_r_list(value):
        return False
    if isinstance(value, (str, bytes, bytearray)):
        return True
    if isinstance(value, (bool, int, float, complex)):
        return True
    if isinstance(value, np.generic):
        return True
    return False


def _all_na_scalar(value) -> bool:
    if value is NA or value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, np.floating) and math.isnan(float(value)):
        return True
    if isinstance(value, complex):
        return math.isnan(value.real) or math.isnan(value.imag)
    if isinstance(value, np.ndarray):
        if value.ndim != 0:
            return False
        return bool(_missing_mask(value))
    try:
        arr = np.asarray(value)
        if arr.ndim == 0:
            return bool(_missing_mask(arr))
    except (TypeError, ValueError):
        pass
    return False


def _all_na_vector(value) -> bool:
    if isinstance(value, np.ndarray):
        return bool(np.all(_missing_mask(value)))
    if isinstance(value, (str, bytes, bytearray)):
        if len(value) == 0:
            return True
        return all(_all_na_scalar(item) for item in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if len(value) == 0:
            return True
        return all(_all_na_scalar(item) for item in value)
    return _all_na_scalar(value)


def invalid(x=_UNSET) -> bool:
    if x is _UNSET or x is None:
        return True
    if isinstance(x, TryError):
        return True
    if _length(x) == 0:
        return True
    if _is_r_list(x):
        if isinstance(x, dict):
            items = x.values()
        else:
            items = x
        return all(invalid(item) for item in items)
    if _is_r_vector(x):
        return _all_na_vector(x)
    return False
