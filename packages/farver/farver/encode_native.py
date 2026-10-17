"""Encode colours as R native raster integers."""

from __future__ import annotations

import numpy as np

from farver._common import as_colour_list, parse_colour
from farver.encode_colour import encode_colour


def _is_character(colour) -> bool:
    if isinstance(colour, str):
        return True
    if isinstance(colour, np.ndarray) and colour.dtype.kind in "SUO":
        return True
    if isinstance(colour, (list, tuple)):
        return all(item is None or isinstance(item, str) for item in colour)
    return False


def _native(red: int, green: int, blue: int, alpha: int) -> int:
    packed = (red & 255) | ((green & 255) << 8) | ((blue & 255) << 16) | ((alpha & 255) << 24)
    return int(np.int32(np.uint32(packed)))


def encode_native(colour, *args, **kwargs):
    """Pack colours into R's 32-bit native integers.

    A matrix is encoded with ``encode_colour`` first. Named colours use
    ``R_RGB``, which forces the alpha byte to 255.
    """
    if not _is_character(colour):
        colour = encode_colour(colour, *args, **kwargs)
    codes = as_colour_list(colour)
    out = []
    for code in codes:
        if code is None or code == "NA":
            raise ValueError("Unknown colour name: NA")
        _missing, red, green, blue, alpha_byte, _unit = parse_colour(
            code, short_ok=False, na_value=None
        )
        if code.startswith("#"):
            alpha = 255 if alpha_byte < 0 else alpha_byte
        else:
            alpha = 255
        out.append(_native(red, green, blue, alpha))
    return out
