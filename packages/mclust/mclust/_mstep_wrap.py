"""Small R-style helpers for the mclust M-step translations.

``mstep_evv`` and ``mstep_vee_eve_vve`` share these. The Fortran is called
through the ``mclust_kernels`` binding; each kernel takes one tuple of the
``.Fortran`` arguments in order and returns all of them, as R does.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

# signif(.Machine$double.xmax, 6)
SIGNIF_XMAX = 1.79769e308

# .Machine$double.eps
MACHINE_EPS = float(np.finfo(float).eps)


def column_major(a: Any) -> list[float]:
    """Flatten in column-major order, the layout R passes to Fortran."""
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def fortran_matrix(values: Any, rows: int, cols: int) -> np.ndarray:
    """``matrix(values, rows, cols)`` from a column-major vector."""
    return np.array(values, dtype=float).reshape((rows, cols), order="F")


def r_warning(message: str, warn: bool) -> None:
    if warn:
        warnings.warn(message, RuntimeWarning, stacklevel=3)


def matrix_data(data: Any, message: str) -> np.ndarray:
    """R's check that ``data`` is a matrix with more than one column."""
    arr = np.asarray(data, dtype=float)
    if arr.ndim != 2 or arr.shape[1] == 1:
        raise ValueError(message)
    return arr


def z_matrix(z: Any, n: int, message: str) -> np.ndarray:
    """``as.matrix(z)`` with the row check of the R code."""
    arr = np.asarray(z, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.shape[0] != n:
        raise ValueError(message)
    return arr


def pick_second(value: Any) -> float:
    """R ``if (length(v) == 1) v else v[2]``, for ``tol`` and ``itmax``."""
    arr = np.atleast_1d(np.asarray(value, dtype=float))
    return float(arr[0]) if arr.size == 1 else float(arr[1])


def prior_params(prior: dict, data: np.ndarray, G: int, model_name: str) -> Any:
    """``do.call(prior$functionName, c(list(data, G, modelName), prior[-1]))``."""
    fn = prior["functionName"]
    if isinstance(fn, str):
        from mclust import model_metadata

        fn = getattr(model_metadata, fn)
    extra = {key: value for key, value in prior.items() if key != "functionName"}
    return fn(data=data, G=G, modelName=model_name, **extra)


def kernel_call(name: str, args: list) -> list:
    """Call one ``mclust_kernels`` function with its argument list."""
    import mclust_kernels

    return getattr(mclust_kernels, name)(tuple(args))
