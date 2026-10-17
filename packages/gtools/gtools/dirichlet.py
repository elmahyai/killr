"""Dirichlet distribution density (gtools 3.9.5 ``ddirichlet``)."""

from __future__ import annotations

import numpy as np
from scipy.special import gammaln


def ddirichlet(x, alpha):
    """Dirichlet density for each row of ``x`` with shape parameters ``alpha``."""
    x_mat = _coerce_x_matrix(x)
    alpha_mat = _coerce_alpha_matrix(alpha, x_mat.shape[0], x_mat.shape[1])
    if x_mat.shape != alpha_mat.shape:
        raise ValueError("Mismatch between dimensions of 'x' and 'alpha'.")

    nrows = x_mat.shape[0]
    pd = np.empty(nrows, dtype=np.float64)
    for i in range(nrows):
        pd[i] = _dirichlet1(x_mat[i], alpha_mat[i])

    invalid = np.any((x_mat < 0) | (x_mat > 1), axis=1)
    pd[invalid] = 0.0
    for i in range(nrows):
        if not _all_equal_numeric(np.sum(x_mat[i]), 1.0):
            pd[i] = 0.0
    return pd


def _dirichlet1(x_row: np.ndarray, alpha_row: np.ndarray) -> float:
    log_d = np.sum(gammaln(alpha_row)) - gammaln(np.sum(alpha_row))
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (alpha_row - 1.0) * np.log(x_row)
    s = np.where((alpha_row == 1.0) & (x_row == 0.0), -np.inf, s)
    return float(np.exp(np.sum(s) - log_d))


def _coerce_x_matrix(x) -> np.ndarray:
    if _is_data_frame(x):
        return np.asarray(x, dtype=np.float64)
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim == 1:
        return arr.reshape(1, -1)
    return arr


def _is_data_frame(x) -> bool:
    module = type(x).__module__
    name = type(x).__name__
    return name == "DataFrame" and module.startswith(("pandas", "polars"))


def _coerce_alpha_matrix(alpha, nrows: int, ncols: int) -> np.ndarray:
    arr = np.asarray(alpha, dtype=np.float64)
    if arr.ndim == 1:
        if arr.size != ncols:
            raise ValueError("Mismatch between dimensions of 'x' and 'alpha'.")
        return np.tile(arr, (nrows, 1))
    if arr.ndim == 2:
        return arr
    raise ValueError("Mismatch between dimensions of 'x' and 'alpha'.")


def _all_equal_numeric(target, current, tolerance: float | None = None) -> bool:
    if tolerance is None:
        tolerance = float(np.sqrt(np.finfo(np.float64).eps))
    target = np.asarray(target, dtype=np.float64).reshape(-1)
    current = np.asarray(current, dtype=np.float64).reshape(-1)
    if target.size != current.size:
        return False
    t_na = np.isnan(target)
    c_na = np.isnan(current)
    if np.any(t_na != c_na):
        return False
    equal = t_na | (target == current)
    if bool(np.all(equal)):
        return True
    target = target[~equal]
    current = current[~equal]
    n = int(target.size)
    scale = float(np.sum(np.abs(target) / n))
    if np.isfinite(scale) and scale > tolerance:
        diff = float(np.sum(np.abs(target - current) / (n * scale)))
    else:
        diff = float(np.sum(np.abs(target - current) / n))
    return bool(np.isfinite(diff) and diff <= tolerance)
