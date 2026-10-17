"""Convert hexadecimal colors to sRGB or linearized RGB.

`hex2RGB` follows colorspace 2.1-4. The first seven characters are kept, each
channel is divided by 255, and `gamma=True` applies the package's `ftrans`
with exponent 2.4.
"""

import math
from collections.abc import Mapping, Sequence

import numpy as np

_HEX = frozenset("0123456789abcdefABCDEF")
_TRUE = frozenset(("T", "TRUE", "True", "true"))
_FALSE = frozenset(("F", "FALSE", "False", "false"))
_COLUMNS = ("R", "G", "B")


class HexRGB:
    """Coordinates of one or more colors.

    `space` is ``sRGB`` when the channels are still gamma-encoded, and
    ``RGB`` when they have been linearized. `coords` is an ``n`` by 3 array.
    `names` is the row names, or None when the input had none.
    """

    __slots__ = ("space", "coords", "names", "columns")

    def __init__(self, space, coords, names):
        self.space = space
        self.coords = coords
        self.names = names
        self.columns = _COLUMNS

    def __str__(self):
        return _format_matrix(self.coords, self.names)


def hex2RGB(x, gamma=False):
    """Convert ``#RRGGBB`` strings to sRGB, or to linearized RGB.

    A string is one color. A list or tuple is a vector of colors. A mapping
    uses its keys as row names. Characters after the seventh are ignored, which
    drops an alpha suffix. An empty input raises ``invalid color matrix``.
    A string that is not seven characters of ``#`` plus hex digits raises
    ``color error - hex values required``.
    """
    linear = _gamma_flag(gamma)
    texts, names = _collect(x)
    if not texts:
        raise ValueError("invalid color matrix")
    rows = []
    for text in texts:
        if not isinstance(text, str):
            raise ValueError("color error - hex values required")
        # substr(x, 0, 7). Start 0 is the first character.
        piece = text[:7]
        if (
            len(piece) != 7
            or piece[0] != "#"
            or any(ch not in _HEX for ch in piece[1:])
        ):
            raise ValueError("color error - hex values required")
        red = int(piece[1:3], 16) / 255.0
        green = int(piece[3:5], 16) / 255.0
        blue = int(piece[5:7], 16) / 255.0
        if linear:
            red = _ftrans(red)
            green = _ftrans(green)
            blue = _ftrans(blue)
        rows.append((red, green, blue))
    coords = np.array(rows, dtype=np.float64)
    return HexRGB("RGB" if linear else "sRGB", coords, names)


def _ftrans(channel):
    """colorspace `ftrans` at gamma 2.4. The cutoff is 0.03928, not 0.04045."""
    if channel > 0.03928:
        return math.pow((channel + 0.055) / 1.055, 2.4)
    return channel / 12.92


def _gamma_flag(gamma):
    """R's `if (gamma)` on one value, including the true and false spellings."""
    if isinstance(gamma, bool):
        return gamma
    if isinstance(gamma, (int, np.integer)):
        return gamma != 0
    if isinstance(gamma, (float, np.floating)):
        if math.isnan(float(gamma)):
            raise ValueError("argument is not interpretable as logical")
        return float(gamma) != 0.0
    if isinstance(gamma, str):
        if gamma in _TRUE:
            return True
        if gamma in _FALSE:
            return False
        raise ValueError("argument is not interpretable as logical")
    if isinstance(gamma, np.ndarray):
        if gamma.size == 0:
            raise ValueError("argument is of length zero")
        if gamma.size > 1:
            raise ValueError("the condition has length > 1")
        return _gamma_flag(gamma.reshape(-1)[0].item())
    if isinstance(gamma, Sequence):
        if len(gamma) == 0:
            raise ValueError("argument is of length zero")
        if len(gamma) > 1:
            raise ValueError("the condition has length > 1")
        return _gamma_flag(gamma[0])
    if gamma is None:
        raise ValueError("argument is of length zero")
    raise ValueError("argument is not interpretable as logical")


def _collect(x):
    if x is None:
        return [], None
    if isinstance(x, str):
        return [x], None
    if isinstance(x, Mapping):
        names = tuple(key if isinstance(key, str) else str(key) for key in x)
        return list(x.values()), names
    if isinstance(x, np.ndarray):
        if x.size == 0:
            return [], None
        return list(x.reshape(-1).tolist()), None
    if isinstance(x, Sequence):
        return list(x), None
    raise ValueError("color error - hex values required")


def _cell(value):
    if value == 0.0:
        return "0"
    if value == 1.0:
        return "1"
    return format(float(value), ".7g")


def _format_matrix(coords, names):
    cells = [[_cell(value) for value in row] for row in np.asarray(coords)]
    if not cells:
        return ""
    if names is None:
        row_labels = [f"[{index},]" for index in range(1, len(cells) + 1)]
    else:
        row_labels = ["" if name is None else str(name) for name in names]
    label_width = max(len(label) for label in row_labels)
    column_widths = [
        max(len(_COLUMNS[column]), max(len(row[column]) for row in cells))
        for column in range(3)
    ]
    header = " " * label_width + " " + " ".join(
        _COLUMNS[column].rjust(column_widths[column]) for column in range(3)
    )
    lines = [header]
    for index, row in enumerate(cells):
        body = " ".join(
            row[column].rjust(column_widths[column]) for column in range(3)
        )
        lines.append(row_labels[index].rjust(label_width) + " " + body)
    return "\n".join(lines)
