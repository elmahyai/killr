"""Extract alpha transparency from color specifications."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from colorspace._cspace_convert import is_color_object


def _convert(value, mode):
    if isinstance(value, str):
        number = int(value, 16)
        return {"numeric": number / 255.0, "integer": number, "character": f"{number:02X}"}[mode]
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        if not 0 <= int(value) <= 255:
            raise ValueError("invalid integer specification of alpha transparency")
        number = int(value)
        return {"numeric": number / 255.0, "integer": number, "character": f"{number:02X}"}[mode]
    number = float(value)
    if not 0 <= number <= 1:
        raise ValueError("invalid numeric specification of alpha transparency")
    rounded = int(round(number * 255 + 0.0001))
    return {"numeric": number, "integer": rounded, "character": f"{rounded:02X}"}[mode]


def extract_transparency(col, mode="numeric", default=1):
    """Return alpha values from hex colors, matrices, or color objects."""
    if mode == "double":
        mode = "numeric"
    if mode == "hexmode":
        mode = "integer"
    if mode not in ("numeric", "integer", "character"):
        raise ValueError("invalid mode")
    if isinstance(default, Sequence) and not isinstance(default, (str, bytes)):
        default = default[0] if default else None
    missing = np.nan if mode == "numeric" else None
    if default is None or (isinstance(default, float) and np.isnan(default)):
        fallback = missing
    else:
        # R's default=1 is a numeric scalar (not an integer alpha code).
        fallback = _convert(float(default), mode) if isinstance(default, int) and default <= 1 else _convert(default, mode)

    if is_color_object(col):
        n = col.coords.shape[0]
        return [fallback] * n
    if isinstance(col, np.ndarray) and col.ndim == 2 and np.issubdtype(col.dtype, np.number):
        n = col.shape[1]
        values = [fallback] * n
        for i in range(n):
            if np.any(np.isnan(col[:, i])):
                values[i] = missing
        return values
    scalar = isinstance(col, str) or not isinstance(col, Sequence)
    values = [col] if scalar else list(col)
    out = []
    for value in values:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            out.append(missing)
        elif isinstance(value, str) and value.startswith("#") and len(value) == 9:
            out.append(_convert(value[7:9], mode))
        else:
            out.append(fallback)
    return out[0] if scalar else out
