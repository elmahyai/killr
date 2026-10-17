"""Enumerate combinations of a vector (gtools 3.9.5 ``combinations``)."""

from __future__ import annotations

import numpy as np


def _validate_nr(name: str, value) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"bad value of {name}")
    if isinstance(value, np.ndarray):
        if value.size != 1:
            raise ValueError(f"bad value of {name}")
        value = value.reshape(()).item()
    if not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"bad value of {name}")
    as_float = float(value)
    if as_float < 1 or as_float != int(as_float):
        raise ValueError(f"bad value of {name}")
    return int(as_float)


def _as_atomic_vector(v) -> np.ndarray:
    if isinstance(v, (str, bytes)):
        raise ValueError("v is either non-atomic or too short")
    if isinstance(v, np.ndarray):
        if v.dtype == object or np.issubdtype(v.dtype, np.character):
            return np.asarray(v, dtype=object).reshape(-1)
        if v.ndim == 0:
            return np.asarray([v.item()])
        return np.asarray(v).reshape(-1)
    if isinstance(v, (list, tuple)):
        if len(v) == 0:
            return np.array([], dtype=np.float64)
        return np.asarray(v, dtype=object if any(isinstance(x, str) for x in v) else None).reshape(
            -1
        )
    return np.asarray([v])


def _unique_sort(v: np.ndarray) -> np.ndarray:
    if v.dtype == object or v.dtype.kind in ("U", "S"):
        order = np.argsort(v, kind="mergesort")
        sorted_v = v[order]
        out: list = []
        for item in sorted_v:
            if not out or item != out[-1]:
                out.append(item)
        return np.array(out, dtype=object)
    return np.unique(v)


def _sub_no_repeats(n: int, r: int, v: np.ndarray) -> np.ndarray:
    dtype = v.dtype
    if r == 0:
        return np.array([], dtype=dtype).reshape(0, 0)
    if r == 1:
        return np.reshape(v[:n], (n, 1))
    if r == n:
        return np.reshape(v[:n], (1, n))
    upper = _sub_no_repeats(n - 1, r - 1, v[1:])
    first_col = np.full((upper.shape[0], 1), v[0], dtype=dtype)
    top = np.hstack([first_col, upper])
    bottom = _sub_no_repeats(n - 1, r, v[1:])
    return np.vstack([top, bottom])


def _sub_repeats_allowed(n: int, r: int, v: np.ndarray) -> np.ndarray:
    dtype = v.dtype
    if r == 0:
        return np.array([], dtype=dtype).reshape(0, 0)
    if r == 1:
        return np.reshape(v[:n], (n, 1))
    if n == 1:
        return np.full((1, r), v[0], dtype=dtype)
    upper = _sub_repeats_allowed(n, r - 1, v)
    first_col = np.full((upper.shape[0], 1), v[0], dtype=dtype)
    top = np.hstack([first_col, upper])
    bottom = _sub_repeats_allowed(n - 1, r, v[1:])
    return np.vstack([top, bottom])


def combinations(
    n,
    r,
    v=None,
    set: bool = True,
    repeats_allowed: bool = False,
):
    """All ``r``-combinations of the first ``n`` elements of ``v``."""
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
        return _sub_repeats_allowed(n, r, v_arr[:n])
    return _sub_no_repeats(n, r, v_arr[:n])
