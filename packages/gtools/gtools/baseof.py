"""Integer to base-n digit expansion (gtools 3.9.5 ``baseOf``)."""

from __future__ import annotations

import numpy as np

_NA_INT = np.int32(-(2**31))
_V_NULL = "v is null"
_V_NON_INTEGER = "non-integer value(s) provided for v."


def _as_integer_vector(v) -> np.ndarray:
    if v is None:
        raise ValueError(_V_NULL)
    if isinstance(v, np.ndarray):
        if v.size == 0:
            return np.array([], dtype=np.int32)
        if np.issubdtype(v.dtype, np.integer):
            flat = np.asarray(v).reshape(-1).astype(np.int64, copy=False)
        elif np.issubdtype(v.dtype, np.floating):
            flat = np.asarray(v, dtype=np.float64).reshape(-1)
            as_int = flat.astype(np.int64)
            if np.any(as_int != flat):
                raise ValueError(_V_NON_INTEGER)
            flat = as_int
        else:
            raise ValueError(_V_NON_INTEGER)
        if np.any((flat < np.iinfo(np.int32).min) | (flat > np.iinfo(np.int32).max)):
            raise ValueError(_V_NON_INTEGER)
        out = flat.astype(np.int32)
        if np.any(out == _NA_INT):
            raise ValueError("missing value where TRUE/FALSE needed")
        return out
    if isinstance(v, (list, tuple)):
        if len(v) == 0:
            return np.array([], dtype=np.int32)
        parts = [_as_integer_vector(item) for item in v]
        return np.concatenate(parts)
    if isinstance(v, (bool, np.bool_)):
        raise ValueError(_V_NON_INTEGER)
    if isinstance(v, int):
        if v < np.iinfo(np.int32).min or v > np.iinfo(np.int32).max:
            raise ValueError(_V_NON_INTEGER)
        out = np.int32(v)
        if out == _NA_INT:
            raise ValueError("missing value where TRUE/FALSE needed")
        return np.array([out], dtype=np.int32)
    if isinstance(v, float):
        if not np.isfinite(v) or float(int(v)) != v:
            raise ValueError(_V_NON_INTEGER)
        return np.array([np.int32(int(v))], dtype=np.int32)
    raise ValueError(_V_NON_INTEGER)


def _base_of_inner(value: int, base: int, length: int) -> np.ndarray:
    if value == int(_NA_INT):
        return np.full(length, _NA_INT, dtype=np.int32)
    if value == 0:
        return np.zeros(length, dtype=np.int32)

    remainder = int(value)
    slots = int(length)
    digits: list[int] = []
    while remainder > 0 or slots > 0:
        digits.insert(0, remainder % base)
        remainder //= base
        slots -= 1
    return np.array(digits, dtype=np.int32)


def baseOf(v, base: int = 10, len: int = 1):
    """Expand integer values into base-``base`` digits, least significant on the right.

    A single value returns a 1-D ``int32`` vector. Several values return a 2-D
    matrix whose rows are padded to a common width.
    """
    values = _as_integer_vector(v)
    if values.size == 0:
        return values

    base = int(base)
    min_len = int(len)

    if values.size == 1:
        return _base_of_inner(int(values[0]), base, min_len)

    rows = [_base_of_inner(int(item), base, min_len) for item in values]
    longest = max(int(row.size) for row in rows)
    return np.vstack([_base_of_inner(int(item), base, longest) for item in values]).astype(
        np.int32, copy=False
    )
