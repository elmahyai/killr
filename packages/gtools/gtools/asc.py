"""Character to ASCII code conversion (gtools 3.9.5 ``asc``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def _char_codes(text: str) -> list[int]:
    return list(text.encode("utf-8"))


def _char_items(char) -> list[tuple[str | None, str]]:
    if isinstance(char, str):
        return [(None, char)]
    if isinstance(char, Mapping):
        return [(str(name), str(value)) for name, value in char.items()]
    if isinstance(char, np.ndarray):
        if char.ndim == 0:
            return [(None, str(char.item()))]
        values = [str(item) for item in char.ravel(order="F")]
        names = None
        if char.dtype.names:
            names = [str(name) for name in char.dtype.names]
        return [
            (names[index] if names and index < len(names) else None, value)
            for index, value in enumerate(values)
        ]
    if isinstance(char, (bytes, bytearray)):
        return [(None, bytes(char).decode("utf-8"))]
    if isinstance(char, Sequence):
        items: list[tuple[str | None, str]] = []
        for item in char:
            if isinstance(item, (list, tuple, dict, np.ndarray)) or isinstance(item, (bytes, bytearray)):
                raise TypeError("character vector expected")
            items.append((None, str(item)))
        return items
    return [(None, str(char))]


def _label(name: str | None, value: str) -> str:
    return value if name is None else name


def _sapply_asc(items: list[tuple[str | None, str]], simplify: bool):
    if not items:
        return {}
    labels = [_label(name, value) for name, value in items]
    codes = [_char_codes(value) for _, value in items]
    if not simplify:
        return {labels[index]: codes[index] for index in range(len(items))}

    lengths = [len(part) for part in codes]
    if len(set(lengths)) != 1:
        return {labels[index]: codes[index] for index in range(len(items))}
    length = lengths[0]
    if length == 0:
        return {labels[index]: codes[index] for index in range(len(items))}

    if length == 1:
        return np.array([part[0] for part in codes], dtype=np.int64)

    matrix = np.empty((length, len(items)), dtype=np.int64)
    for index, part in enumerate(codes):
        matrix[:, index] = part
    return matrix


def asc(char, simplify=True):
    """Return integer ASCII/UTF-8 byte values for each character string.

    With ``simplify=True``, equal-length results become a vector or matrix like
    R ``sapply(..., simplify=TRUE)``. With ``simplify=False``, the result is a
    dict mapping each input element to its code vector.
    """
    simplify = bool(simplify)
    items = _char_items(char)
    return _sapply_asc(items, simplify)
