"""Create sRGB color objects (colorspace 2.1-4)."""

from collections.abc import Sequence

import numpy as np

from colorspace.hex2rgb import HexRGB

_MISSING = object()
_COLUMNS = ("R", "G", "B")


def sRGB(R=_MISSING, G=_MISSING, B=_MISSING, names=_MISSING):
    """Build an sRGB color from red, green, and blue intensities."""
    if R is _MISSING:
        return HexRGB("sRGB", np.zeros((0, 0), dtype=np.float64), None)
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
    return HexRGB("sRGB", coords, row_names)


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
