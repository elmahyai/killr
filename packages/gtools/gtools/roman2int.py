"""Convert Roman numerals to integers (gtools 3.9.5 ``roman2int``)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

import roman2int as _roman2int

_NA_INTEGER = -2_147_483_648


def _try_one(text: str) -> float:
    try:
        value = int(_roman2int.inner(text))
    except ValueError:
        return np.nan
    if value == _NA_INTEGER:
        return np.nan
    return float(value)


def _is_missing(item) -> bool:
    if item is None:
        return True
    if isinstance(item, float) and np.isnan(item):
        return True
    if isinstance(item, np.floating) and np.isnan(item):
        return True
    return False


def _as_character_vector(roman) -> list[str | None]:
    if isinstance(roman, str):
        return [roman]
    if isinstance(roman, np.ndarray):
        flat = roman.ravel(order="C")
        out: list[str | None] = []
        for item in flat:
            if _is_missing(item):
                out.append(None)
            else:
                out.append(str(item))
        return out
    if isinstance(roman, Sequence) and not isinstance(roman, (bytes, bytearray)):
        out = []
        for item in roman:
            if _is_missing(item):
                out.append(None)
            else:
                out.append(str(item))
        return out
    if _is_missing(roman):
        return [None]
    return [str(roman)]


def roman2int(roman):
    """Convert roman numerals to integers, ignoring case and beyond 3899."""
    pieces = _as_character_vector(roman)
    values = [np.nan if part is None else _try_one(part.strip().upper()) for part in pieces]
    if len(values) == 1 and isinstance(roman, str):
        return values[0]
    return np.asarray(values, dtype=np.float64)
