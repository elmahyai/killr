"""R ``shapeO``: scale orientation slices and form the symmetric shape."""

from __future__ import annotations

import numpy as np
from mclustbootstraplrt import shapeo


def shapeO(shape, O, transpose=False):
    """Match ``mclust:::shapeO``. A matrix ``O`` is returned with a trailing dimension of 1."""
    arr = np.asarray(O, dtype=float)
    if arr.ndim < 2:
        raise ValueError("O must be a matrix or an array")
    if arr.shape[0] != arr.shape[1]:
        raise ValueError("leading dimensions of O are unequal")
    if arr.ndim == 2:
        arr = arr[:, :, None]
    elif arr.ndim != 3:
        raise ValueError("O must be a matrix or an array")
    scale = np.asarray(shape, dtype=float).ravel(order="F")
    if scale.size != arr.shape[0]:
        raise ValueError("dimension of O and length s are unequal")
    out = shapeo(
        bool(transpose),
        np.asarray(scale, dtype=np.float64),
        np.asarray(arr, dtype=np.float64),
    )
    return np.asarray(out, dtype=float)


shape_o = shapeO
