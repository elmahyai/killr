"""lp: R's lp(), the local-polynomial design matrix with its attributes.

R's lp() cbinds its arguments, names the columns from the call, and sets the
attributes alpha = c(nn, h, adpen), deg, acri, style and scale. Here the
matrix is a numpy array subclass that carries the same attributes. Column
names come only from keyword arguments, because R deparses the argument
expressions and Python cannot.
"""

from __future__ import annotations

import numpy as np


class LpMatrix(np.ndarray):
    """A numeric matrix with the attributes R's lp() sets."""

    alpha = None
    deg = 2
    acri = "none"
    style = "none"
    scale = False
    colnames = None

    def __array_finalize__(self, obj):
        if obj is None:
            return
        for name in ("alpha", "deg", "acri", "style", "scale", "colnames"):
            setattr(self, name, getattr(obj, name, getattr(type(self), name)))


def lp(*args, nn=None, h=None, adpen=None, deg=2, acri="none", scale=False,
       style="none", **named):
    cols, names = [], []
    for a in args:
        arr = np.asarray(a, dtype=float)
        arr = arr.reshape(-1, 1) if arr.ndim == 1 else arr
        cols.append(arr)
        names.extend([None] * arr.shape[1])
    for key, a in named.items():
        arr = np.asarray(a, dtype=float).reshape(-1, 1)
        cols.append(arr)
        names.append(key)
    if not cols:
        raise ValueError("lp needs at least one variable")
    # R: if nn, h and adpen are all missing, nn = 0.7; the rest default to 0.
    if nn is None and h is None and adpen is None:
        nn = 0.7
    alpha = np.array([0.0 if nn is None else nn,
                      0.0 if h is None else h,
                      0.0 if adpen is None else adpen], dtype=float)
    out = np.ascontiguousarray(np.hstack(cols)).view(LpMatrix)
    out.alpha = alpha
    out.deg = deg
    out.acri = acri
    out.style = style
    out.scale = scale
    out.colnames = names
    return out
