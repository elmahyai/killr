"""Independent component analysis (e1071 ``ica``)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import numpy as np

_FUNLIST = ("negative kurtosis", "positive kurtosis", "4th moment")


def _pmatch(value, choices):
    text = str(value)
    hits = [index for index, choice in enumerate(choices) if choice.startswith(text)]
    if not hits:
        return None
    if len(hits) > 1:
        return -1
    return hits[0]


def _norm_rand():
    try:
        from mass._r_rng import norm_rand
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "MASS"))
        from mass._r_rng import norm_rand
    return norm_rand()


def _resolve_fun(fun):
    if callable(fun):
        return fun, None
    index = _pmatch(fun, _FUNLIST)
    if index is None or index < 0:
        raise ValueError("ica: invalid fun")
    funname = _FUNLIST[index]
    if index == 0:
        nonlinear: Callable[[np.ndarray], np.ndarray] = np.tanh
    elif index == 1:

        def nonlinear(x):
            return x - np.tanh(x)

    else:

        def nonlinear(x):
            return np.sign(x) * x**2

    return nonlinear, funname


def _as_matrix(x):
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError("ica: X must be a matrix or a data frame")
    if array.dtype.kind not in "iufc":
        raise ValueError("ica: X contains non numeric elements")
    return array.astype(float, copy=False)


def ica(x, lrate, epochs=100, ncomp=None, fun="negative"):
    """Extract independent components with a nonlinear PCA algorithm."""
    matrix = _as_matrix(x)
    m, n = matrix.shape
    if ncomp is None:
        ncomp = n
    ncomp = int(ncomp)

    draws = [_norm_rand() for _ in range(ncomp * n)]
    w_init = np.array(draws, dtype=float).reshape(n, ncomp).T.copy()
    w = w_init.copy()

    nonlinear, funname = _resolve_fun(fun)
    if funname is None:
        funname = getattr(fun, "__name__", str(fun))

    lrate = float(lrate)
    epochs = int(epochs)

    for _ in range(epochs):
        for j in range(m):
            row = matrix[j : j + 1, :]
            y = w @ row.T
            gy = nonlinear(y)
            w = w + lrate * (gy @ (row - (gy.T @ w)))

    projection = matrix @ w.T

    return {
        "weights": w,
        "projection": projection,
        "epochs": epochs,
        "fun": funname,
        "lrate": lrate,
        "initweights": w_init,
    }
