"""Decode R native raster integers to hex strings."""

from __future__ import annotations

import numpy as np

_NA = -2147483648
_HEX = "0123456789ABCDEF"


def _byte(value: int, shift: int) -> int:
    return (int(np.uint32(np.int32(value))) >> shift) & 255


def _hex_byte(value: int) -> str:
    return _HEX[value >> 4] + _HEX[value & 15]


def decode_native(colour):
    """Turn native integers back into ``#RRGGBB`` or ``#RRGGBBAA``."""
    if isinstance(colour, np.ndarray):
        values = colour.astype(np.int32, copy=False).ravel().tolist()
    elif isinstance(colour, (list, tuple)):
        values = list(colour)
    else:
        values = [colour]
    out = []
    for value in values:
        if value is None:
            out.append(None)
            continue
        number = int(value)
        if number == _NA:
            out.append(None)
            continue
        red = _byte(number, 0)
        green = _byte(number, 8)
        blue = _byte(number, 16)
        alpha = _byte(number, 24)
        text = "#" + _hex_byte(red) + _hex_byte(green) + _hex_byte(blue)
        if alpha != 255:
            text += _hex_byte(alpha)
        out.append(text)
    return out
