"""Convert objects to byte-size vectors."""

from __future__ import annotations

import re
from collections.abc import Sequence

import numpy as np

from rlang import RLangError, abort

_BYTE_PATTERN = re.compile(
    r"^(?P<size>[\d.]+)\s*(?P<unit>[kKMGTPEZY]?)i?[Bb]?$"
)

_BYTE_UNITS = {
    "B": 1.0,
    "k": 1000.0,
    "K": 1000.0,
    "M": 1000.0**2,
    "G": 1000.0**3,
    "T": 1000.0**4,
    "P": 1000.0**5,
    "E": 1000.0**6,
    "Z": 1000.0**7,
    "Y": 1000.0**8,
}


class Bytes:
    """Numeric byte sizes (R ``rlib_bytes``)."""

    __slots__ = ("_data",)

    def __init__(self, data: Sequence[float] | np.ndarray):
        self._data = np.asarray(data, dtype=float)

    def unclass(self) -> np.ndarray:
        return self._data.copy()


def _is_bytes(x: object) -> bool:
    return isinstance(x, Bytes)


def new_bytes(x: Sequence[float] | np.ndarray | None = None) -> Bytes:
    if x is None:
        return Bytes(np.array([], dtype=float))
    return Bytes(x)


def _parse_bytes_strings(x: Sequence[str]) -> Bytes:
    values = np.empty(len(x), dtype=float)
    for index, item in enumerate(x):
        match = _BYTE_PATTERN.fullmatch(item)
        if match is None:
            values[index] = np.nan
            continue
        size = float(match.group("size"))
        unit = match.group("unit") or "B"
        values[index] = size * _BYTE_UNITS[unit]
    return new_bytes(values)


def _is_numeric_sequence(x: object) -> bool:
    if isinstance(x, (str, bytes, Bytes)):
        return False
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        return True
    if isinstance(x, np.ndarray):
        return x.dtype.kind in "iuf" and x.ndim > 0
    if isinstance(x, Sequence):
        if not x:
            return True
        return all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in x)
    return False


def _is_character_sequence(x: object) -> bool:
    if isinstance(x, str):
        return True
    if isinstance(x, Sequence) and not isinstance(x, (bytes, bytearray)):
        if not x:
            return True
        return all(isinstance(item, str) for item in x)
    return False


def as_bytes(x: object) -> Bytes:
    if _is_bytes(x):
        return x
    if _is_character_sequence(x):
        if isinstance(x, str):
            return _parse_bytes_strings([x])
        return _parse_bytes_strings(list(x))
    if _is_numeric_sequence(x):
        if isinstance(x, (int, float)):
            return new_bytes([float(x)])
        return new_bytes(x)
    cls = type(x).__name__
    abort(f"no applicable method for 'as_bytes' applied to an object of class \"{cls}\"")
    raise RLangError("unreachable")
