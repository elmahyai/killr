"""Create RGB color objects (colorspace 2.1-4)."""

import math
from collections.abc import Sequence

import numpy as np

_MISSING = object()
_COLUMNS = ("R", "G", "B")


class RGBColor:
    """Coordinates of one or more colors in linearized sRGB space."""

    __slots__ = ("space", "coords", "names", "columns")

    def __init__(self, coords, names):
        self.space = "RGB"
        self.coords = coords
        self.names = names
        self.columns = _COLUMNS

    def __str__(self):
        return _format_matrix(self.coords, self.names)


def RGB(R=_MISSING, G=_MISSING, B=_MISSING, names=_MISSING):
    """Build an RGB color from red, green, and blue intensities."""
    if R is _MISSING:
        return RGBColor(np.zeros((0, 0), dtype=np.float64), None)
    r_input = R
    if isinstance(R, tuple) and len(R) == 2 and not isinstance(R[0], (str, bytes)):
        r_input, embedded_names = R
        if names is _MISSING:
            names = embedded_names
    r_arr = _as_float_array(r_input)
    if r_arr.dtype.kind == "i":
        r_arr = r_arr.astype(np.float64)
    else:
        r_arr = np.asarray(r_arr, dtype=np.float64)
    if names is _MISSING:
        row_names = None
    elif names is None:
        row_names = None
    else:
        row_names = tuple(str(n) for n in names)
    if G is _MISSING and B is _MISSING:
        coords = np.asarray(r_arr, dtype=np.float64)
        if coords.ndim != 2 or coords.shape[1] != 3:
            raise ValueError("invalid color matrix")
    else:
        n = r_arr.size if r_arr.ndim == 1 else r_arr.shape[0]
        cols = [_recycle_column(r_arr, n)]
        if G is not _MISSING:
            cols.append(_recycle_column(G, n))
        if B is not _MISSING:
            cols.append(_recycle_column(B, n))
        coords = np.column_stack(cols)
    _check_matrix(coords)
    return RGBColor(coords, row_names)


def _recycle_column(value, n):
    arr = np.ravel(_as_float_array(value)).astype(np.float64)
    if arr.size == 1:
        return np.full(n, arr[0], dtype=np.float64)
    if arr.size != n:
        raise ValueError("invalid color matrix")
    return arr


def _as_float_array(value):
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return np.asarray(list(value))
    return np.asarray([value])


def _check_matrix(coords):
    arr = np.asarray(coords)
    if arr.dtype.kind != "f" or arr.size < 1 or arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError("invalid color matrix")


def _format_value(value):
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return "NaN"
    if value == 0.0:
        return "0"
    if value == 1.0:
        return "1"
    return format(float(value), ".7g")


def _format_matrix(coords, names):
    arr = np.asarray(coords, dtype=np.float64)
    if arr.size == 0:
        return "<0 x 0 matrix>"
    cells = [[_format_value(value) for value in row] for row in arr]
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
