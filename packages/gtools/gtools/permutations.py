"""Enumerate permutations of a vector (gtools 3.9.5 ``permutations``)."""

from __future__ import annotations

import numpy as np

from gtools.combinations import _as_atomic_vector, _unique_sort, _validate_nr


def _perm_no_repeats(n: int, r: int, v: np.ndarray) -> np.ndarray:
    dtype = v.dtype
    if r == 1:
        return np.reshape(v[:n], (n, 1))
    if n == 1:
        return np.full((1, r), v[0], dtype=dtype)
    parts: list[np.ndarray] = []
    for i in range(n):
        rest = np.delete(v[:n], i)
        sub = _perm_no_repeats(n - 1, r - 1, rest)
        first_col = np.full((sub.shape[0], 1), v[i], dtype=dtype)
        parts.append(np.hstack([first_col, sub]))
    return np.vstack(parts)


def _perm_repeats_allowed(n: int, r: int, v: np.ndarray) -> np.ndarray:
    dtype = v.dtype
    if r == 1:
        return np.reshape(v[:n], (n, 1))
    if n == 1:
        return np.full((1, r), v[0], dtype=dtype)
    inner = _perm_repeats_allowed(n, r - 1, v)
    n_inner = inner.shape[0]
    first_col = np.repeat(v[:n], n_inner).reshape(-1, 1)
    # R: matrix(t(inner), ncol=ncol(inner), nrow=nrow(inner)*n, byrow=TRUE)
    tail = np.tile(inner, (n, 1))
    return np.hstack([first_col, tail])


def permutations(
    n,
    r,
    v=None,
    set: bool = True,
    repeats_allowed: bool = False,
):
    """All ``r``-permutations of the first ``n`` elements of ``v``."""
    n = _validate_nr("n", n)
    r = _validate_nr("r", r)

    if v is None:
        v_arr = np.arange(1, n + 1, dtype=np.float64)
    else:
        v_arr = _as_atomic_vector(v)

    if v_arr.dtype == object and v_arr.size == 0:
        raise ValueError("v is either non-atomic or too short")
    if v_arr.size < n:
        raise ValueError("v is either non-atomic or too short")

    if r > n and not repeats_allowed:
        raise ValueError("r > n and repeats.allowed=FALSE")

    if set:
        v_arr = _unique_sort(v_arr)
        if v_arr.size < n:
            raise ValueError("too few different elements")

    if repeats_allowed:
        return _perm_repeats_allowed(n, r, v_arr[:n])
    return _perm_no_repeats(n, r, v_arr[:n])
