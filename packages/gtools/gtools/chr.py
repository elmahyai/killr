"""ASCII codes to character strings (gtools 3.9.5 ``chr``)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np

_NA_INT = np.int32(-(2**31))


def _is_missing_code(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, np.floating):
        return math.isnan(float(value))
    try:
        return np.int32(value) == _NA_INT
    except (TypeError, ValueError, OverflowError):
        return False


def _to_byte(value) -> int:
    if _is_missing_code(value):
        return 0
    number = int(value)
    if number < 0 or number > 255:
        return 0
    return number


def _scalar_to_str(code) -> str:
    byte = _to_byte(code)
    if byte == 0:
        return ""
    return bytes([byte]).decode("latin-1")


def _codes_to_bytes(codes) -> bytes:
    array = np.asarray(codes, dtype=np.float64).ravel()
    if array.size == 0:
        return b""
    return bytes(_to_byte(item) for item in array)


def _unit_to_str(unit) -> str:
    if isinstance(unit, (list, tuple, np.ndarray)):
        array = np.asarray(unit, dtype=np.float64).ravel()
        if array.size == 1:
            return _scalar_to_str(array[0])
        return _codes_to_bytes(unit).decode("latin-1")
    if isinstance(unit, (bytes, bytearray)):
        raw = _codes_to_bytes(list(unit))
        if len(raw) == 1 and raw[0] == 0:
            return ""
        return raw.decode("latin-1")
    return _scalar_to_str(unit)


def _ascii_units(ascii):
    if isinstance(ascii, Mapping):
        return [(str(name), value) for name, value in ascii.items()]
    if isinstance(ascii, np.ndarray):
        if ascii.ndim == 0:
            return [(None, ascii.item())]
        flat = ascii.ravel(order="F")
        return [(None, flat[index].item()) for index in range(flat.size)]
    if isinstance(ascii, list):
        return [(None, item) for item in ascii]
    if isinstance(ascii, (int, float, np.integer, np.floating)):
        return [(None, ascii)]
    if isinstance(ascii, Sequence):
        return [(None, item) for item in ascii]
    return [(None, ascii)]


def chr(ascii):
    """Return character strings for integer ASCII byte codes.

    Like R ``sapply(ascii, function(x) rawToChar(as.raw(x)))``: atomic and
    matrix inputs apply per element; list or dict values may be code vectors
    that become one string each.
    """
    units = _ascii_units(ascii)
    if not units:
        return []

    names = [name for name, _ in units]
    values = [_unit_to_str(unit) for _, unit in units]

    if names[0] is not None and all(name is not None for name in names):
        return {name: value for name, value in zip(names, values)}

    return np.array(values, dtype=object)
