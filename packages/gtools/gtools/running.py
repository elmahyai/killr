"""Rolling windows on a vector (gtools 3.9.5 ``running``)."""

from __future__ import annotations

import math

import numpy as np

__all__ = ["running"]

_ALIGNMENTS = ("right", "center", "left")


def running(
    X,
    Y=None,
    fun=None,
    width=None,
    allow_fewer=False,
    pad=False,
    align="right",
    simplify=True,
    by=None,
    **kwargs,
):
    """Apply ``fun`` over sequential windows of ``X`` (and optionally ``Y``)."""
    if fun is None:
        fun = np.mean
    align = _match_arg(align, _ALIGNMENTS)
    x_vec = _as_vector(X)
    n = len(x_vec)
    if n == 0:
        return np.asarray([], dtype=float) if simplify else []
    if width is None:
        width = min(n, 20)
    width = int(width)
    if width < 1:
        raise ValueError("width must be at least 1")

    from_idx, to_idx = _window_bounds(n, width, align)
    elements = _window_index_lists(from_idx, to_idx)
    names = [f"{a}:{b}" for a, b in zip(from_idx, to_idx, strict=True)]
    m = len(elements)

    if not allow_fewer:
        skip = np.array([len(idx) < width for idx in elements], dtype=bool)
    else:
        skip = np.zeros(m, dtype=bool)

    run_elements = [elements[i] for i in range(m) if not skip[i]]
    run_names = [names[i] for i in range(m) if not skip[i]]

    if by is not None:
        by = int(by)
        picks = list(range(0, len(run_elements), by))
        run_elements = [run_elements[i] for i in picks]
        run_names = [run_names[i] for i in picks]

    if Y is None:
        results = [_call_uni(fun, x_vec, which, kwargs) for which in run_elements]
    else:
        y_vec = _as_vector(Y)
        if len(y_vec) != n:
            raise ValueError("X and Y must have the same length")
        results = [
            _call_bi(fun, x_vec, y_vec, which, kwargs) for which in run_elements
        ]

    if simplify:
        xvar = _simplify(results, run_names)
    else:
        xvar = _named_list(results, run_names)

    if allow_fewer or not pad or not simplify:
        return xvar

    return _pad_simplified(xvar, skip, names, m, run_names)


def _match_arg(value, choices):
    if value not in choices:
        raise ValueError(
            f"'align' should be one of {', '.join(repr(c) for c in choices)}"
        )
    return value


def _as_vector(x):
    if isinstance(x, np.ndarray):
        flat = x.reshape(-1)
        if flat.dtype == object:
            return flat
        return flat.astype(float, copy=False)
    if isinstance(x, str):
        return np.asarray(list(x), dtype=object)
    if isinstance(x, (list, tuple)):
        if not x:
            return np.asarray([], dtype=float)
        if _needs_object(x):
            return np.asarray(list(x), dtype=object)
        return np.asarray(x, dtype=float).reshape(-1)
    return np.asarray([float(x)], dtype=float)


def _needs_object(seq):
    for item in seq:
        if isinstance(item, str):
            return True
        if item is None:
            return True
        if isinstance(item, float) and math.isnan(item):
            return True
    return False


def _window_bounds(n, width, align):
    one = np.arange(1, n + 1, dtype=np.int64)
    if align == "left":
        from_idx = one.copy()
        to_idx = np.minimum(one + width - 1, n)
    elif align == "right":
        from_idx = np.maximum(one - width + 1, 1)
        to_idx = one.copy()
    else:
        if width % 2 != 1:
            raise ValueError("width must be odd for center alignment")
        # R: pmax((2 - width):n, 1) and pmin(1:(n + width - 1), n)
        from_idx = np.maximum(np.arange(2 - width, n + 1, dtype=np.int64), 1)
        to_idx = np.minimum(np.arange(1, n + width, dtype=np.int64), n)
    return from_idx.tolist(), to_idx.tolist()


def _window_index_lists(from_idx, to_idx):
    return [list(range(a, b + 1)) for a, b in zip(from_idx, to_idx, strict=True)]


def _call_uni(fun, x_vec, which, kwargs):
    return fun(_take_1based(x_vec, which), **kwargs)


def _call_bi(fun, x_vec, y_vec, which, kwargs):
    return fun(
        _take_1based(x_vec, which),
        _take_1based(y_vec, which),
        **kwargs,
    )


def _take_1based(vec, which):
    idx = [i - 1 for i in which]
    if isinstance(vec, np.ndarray):
        return vec.take(idx)
    return [vec[i] for i in idx]


def _simplify(results, names):
    if not results:
        return np.asarray([], dtype=float)
    if all(_is_scalar(r) for r in results):
        return np.asarray([_scalar_value(r) for r in results], dtype=float)
    lengths = {len(np.asarray(r).reshape(-1)) for r in results}
    if len(lengths) != 1:
        return _named_list(results, names)
    length = next(iter(lengths))
    cols = [np.asarray(r, dtype=float).reshape(-1) for r in results]
    mat = np.column_stack(cols)
    if length == 1:
        return mat.reshape(-1)
    return mat


def _is_scalar(value):
    if value is None:
        return True
    return np.asarray(value).size <= 1


def _scalar_value(value):
    if value is None:
        return math.nan
    arr = np.asarray(value, dtype=float).reshape(-1)
    if arr.size == 0:
        return math.nan
    return float(arr[0])


def _named_list(results, names):
    return dict(zip(names, results, strict=True))


def _pad_simplified(xvar, skip, all_names, m, run_names):
    if isinstance(xvar, dict):
        return xvar
    arr = np.asarray(xvar, dtype=float)
    if arr.ndim == 2:
        whole = np.full((arr.shape[0], m), math.nan, dtype=float)
        if arr.shape[1] == int(np.sum(~skip)):
            whole[:, ~skip] = arr
        return whole
    whole = np.full(m, math.nan, dtype=float)
    values = arr.reshape(-1)
    if len(run_names) == len(values):
        for nm, val in zip(run_names, values, strict=True):
            whole[all_names.index(nm)] = val
        return whole
    if len(values) == int(np.sum(~skip)):
        whole[~skip] = values
    return whole
