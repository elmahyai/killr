"""Shared vector helpers for the data.table translation."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

NA_INTEGER = -2147483648


class DataTableError(Exception):
    """An error raised with data.table's message."""


def is_na(value) -> bool:
    if value is None:
        return True
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (float, np.floating)):
        return bool(math.isnan(float(value)))
    return False


def is_xts(value) -> bool:
    classes = getattr(value, "r_class", None)
    if classes is None:
        return False
    if isinstance(classes, str):
        classes = [classes]
    return "xts" in classes


def is_integer64(value) -> bool:
    classes = getattr(value, "r_class", None)
    if classes is None:
        return False
    if isinstance(classes, str):
        classes = [classes]
    return "integer64" in classes


def as_sequence(value):
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return [value.item()]
        if value.ndim > 1:
            return value
        return value.tolist()
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def column_list(value) -> bool:
    """True when value is an R list of columns, not an atomic vector."""
    if isinstance(value, np.ndarray):
        return False
    if isinstance(value, str) or not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return False
    if len(value) == 0:
        return False
    return all(isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)) for item in value)


def r_type(value) -> str:
    if isinstance(value, (bool, np.bool_)):
        return "logical"
    if isinstance(value, (int, np.integer)):
        return "integer"
    if isinstance(value, (float, np.floating)):
        return "double"
    if isinstance(value, str):
        return "character"
    if value is None:
        return "logical"
    return type(value).__name__


def vector_type(values) -> str:
    seen = None
    for value in values:
        if is_na(value):
            continue
        kind = r_type(value)
        if seen is None:
            seen = kind
        elif seen != kind:
            return "mixed"
    return "logical" if seen is None else seen
