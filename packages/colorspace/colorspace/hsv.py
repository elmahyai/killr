"""Create HSV color objects (colorspace 2.1-4)."""

import math
from collections.abc import Sequence

import numpy as np

_MISSING = object()
_COLUMNS = ("H", "S", "V")


class HSVColor:
    """Coordinates of one or more colors in HSV space."""

    __slots__ = ("space", "coords", "names", "columns")

    def __init__(self, coords, names):
        self.space = "HSV"
        self.coords = coords
        self.names = names
        self.columns = _COLUMNS

    def __str__(self):
        return _format_matrix(self.coords, self.names)


def HSV(H=_MISSING, S=_MISSING, V=_MISSING, names=_MISSING):
    """Build an HSV color from hue, saturation, and value."""
    if H is _MISSING:
        return HSVColor(np.zeros((0, 0), dtype=np.float64), None)
    h_input = H
    if isinstance(H, tuple) and len(H) == 2 and not isinstance(H[0], (str, bytes)):
        h_input, embedded_names = H
        if names is _MISSING:
            names = embedded_names
    h_arr = _as_float_array(h_input)
    if h_arr.dtype.kind == "i":
        h_arr = h_arr.astype(np.float64)
    else:
        h_arr = np.asarray(h_arr, dtype=np.float64)
    if names is _MISSING:
        row_names = None
    elif names is None:
        row_names = None
    else:
        row_names = tuple(str(n) for n in names)
    if S is _MISSING and V is _MISSING:
        coords = np.asarray(h_arr, dtype=np.float64)
        if coords.ndim != 2 or coords.shape[1] != 3:
            raise ValueError("invalid color matrix")
    else:
        n = h_arr.size if h_arr.ndim == 1 else h_arr.shape[0]
        cols = [_recycle_column(h_arr, n)]
        if S is not _MISSING:
            cols.append(_recycle_column(S, n))
        if V is not _MISSING:
            cols.append(_recycle_column(V, n))
        coords = np.column_stack(cols)
    _check_matrix(coords)
    return HSVColor(coords, row_names)


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
