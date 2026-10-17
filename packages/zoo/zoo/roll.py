"""Rolling means, sums, maxima, medians, and a general window apply.

Width is the R width. ``partial``, ``align``, and ``fill`` follow ``rollapply``
and ``na.fill`` in zoo 1.9-1. A ``roll*r`` function is the right-aligned wrapper.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np

from zoo.series import Zoo


class _Missing:
    """Marks an argument the caller did not supply."""


_MISSING = _Missing()
_ALIGN = ("center", "left", "right")


def _match_arg(arg: Any, choices: tuple[str, ...]) -> str:
    """R ``match.arg``. ``None`` and the full choice vector select the first."""
    if arg is None or arg is _MISSING:
        return choices[0]
    if isinstance(arg, (list, tuple)) and list(arg) == list(choices):
        return choices[0]
    if not isinstance(arg, str):
        text = ", ".join(repr(choice) for choice in choices)
        raise ValueError(f"'arg' should be one of {text}")
    matches = [choice for choice in choices if choice.startswith(arg)]
    if len(matches) == 1 and arg != "":
        return matches[0]
    text = ", ".join(repr(choice) for choice in choices)
    raise ValueError(f"'arg' should be one of {text}")


def _is_zoo(obj: Any) -> bool:
    return isinstance(obj, Zoo)


def _values(obj: Any) -> np.ndarray:
    if _is_zoo(obj):
        return np.asarray(obj.data)
    return np.asarray(obj)


def _length(obj: Any) -> int:
    if _is_zoo(obj):
        return len(obj)
    return int(np.asarray(obj).size)


def _nrow(obj: Any) -> int:
    arr = _values(obj)
    if arr.ndim == 0:
        return 1
    return int(arr.shape[0])


def _is_matrix(obj: Any) -> bool:
    return _values(obj).ndim == 2


def _any_na(arr: Any) -> bool:
    values = np.asarray(arr)
    if values.size == 0 or not np.issubdtype(values.dtype, np.floating):
        return False
    return bool(np.isnan(values).any())


def _as_zoo(obj: Any) -> Zoo:
    if _is_zoo(obj):
        return obj
    arr = np.asfortranarray(np.asarray(obj))
    if arr.ndim == 0:
        arr = arr.reshape(1)
    n = int(arr.shape[0])
    return Zoo(arr, np.arange(1, n + 1))


def _copy_zoo(data: np.ndarray, source: Zoo, index: Any) -> Zoo:
    out = Zoo(data, index, source.frequency, source.regular)
    names = getattr(source, "colnames", None)
    if names is not None:
        out.colnames = list(names)
    return out


def _take_index(index: Any, selector: Any) -> Any:
    if isinstance(index, np.ndarray):
        return np.array(index[selector], copy=True)
    items = list(index)
    chosen = np.asarray(selector)
    if chosen.dtype == bool:
        return [items[i] for i, keep in enumerate(chosen) if keep]
    return [items[int(i)] for i in chosen]


def _partial_code(partial: Any) -> float:
    if isinstance(partial, (bool, np.bool_)):
        return 1.0 if bool(partial) else -1.0
    return float(partial)


def _trunc_int(value: Any) -> int:
    return int(math.trunc(float(value)))


def _width_offsets(width: int, align: str) -> np.ndarray:
    if width < 0:
        raise ValueError("invalid 'length.out'")
    if width == 0:
        return np.array([], dtype=int)
    if align == "right":
        return np.arange(1 - width, 1)
    if align == "center":
        end = math.floor(width / 2)
        start = end - (width - 1)
        return np.arange(start, end + 1)
    return np.arange(0, width)


def _is_offset_spec(width: Any) -> bool:
    if isinstance(width, (str, bytes)) or isinstance(width, np.ndarray):
        return False
    if not isinstance(width, (list, tuple)):
        return False
    for item in width:
        if item is None or isinstance(item, (list, tuple, np.ndarray)):
            return True
    return False


def _offset_vector(item: Any) -> np.ndarray | None:
    if item is None:
        return None
    return np.trunc(np.asarray(item, dtype=float)).astype(int)


def _seq_1(start: int, end: int, by: Any) -> list[int]:
    step = float(by)
    if step == 0:
        raise ValueError("invalid '(to - from)/by'")
    if float(step).is_integer():
        return list(range(int(start), int(end) + (1 if step > 0 else -1), int(step)))
    out: list[int] = []
    x = float(start)
    if step > 0:
        while x <= end + 1e-8:
            out.append(int(round(x)))
            x += step
    else:
        while x >= end - 1e-8:
            out.append(int(round(x)))
            x += step
    return out


def _recycle_offsets(offsets: list[np.ndarray | None], n: int, by: Any, partial: float) -> list:
    if len(offsets) == 1:
        placed: list[np.ndarray | None] = [None] * n
        one = offsets[0]
        if partial < 0:
            if one is None or len(one) == 0:
                start = 1
            else:
                start = max(-int(np.min(one)), 0) + 1
        else:
            start = 1
        start = min(n, start) if n else start
        if n and start >= 1:
            for pos in _seq_1(start, n, by):
                placed[pos - 1] = None if one is None else np.array(one, copy=True)
        return placed
    return [offsets[i % len(offsets)] for i in range(n)]


def _prepare_offsets(width: Any, n: int, align: str, by: Any, partial: float) -> list:
    if _is_offset_spec(width):
        offsets = [_offset_vector(item) for item in width]
    else:
        flat = np.atleast_1d(np.asarray(width, dtype=float)).reshape(-1)
        offsets = [_width_offsets(_trunc_int(item), align) for item in flat]
    if not offsets:
        raise ValueError("invalid width")
    return _recycle_offsets(offsets, n, by, partial)


def _align_ix(n: int, k: int, align: str) -> np.ndarray:
    if align == "left":
        return np.arange(1, n - k + 2)
    if align == "right":
        return np.arange(k, n + 1)
    start = math.floor((1 + k) / 2)
    end = math.ceil(n - k / 2.0)
    return np.arange(start, end + 1)


def _fill_components(fill: Any) -> list[Any]:
    if fill is None:
        items: list[Any] = []
    elif isinstance(fill, (str, bytes)):
        items = [fill]
    elif isinstance(fill, (list, tuple)):
        items = list(fill)
    elif isinstance(fill, np.ndarray):
        items = [fill.reshape(-1)[i].item() for i in range(fill.size)]
    else:
        items = [fill]
    if not items:
        return [None, None, None]
    return [items[i % len(items)] for i in range(3)]


def _component_empty(component: Any) -> bool:
    if component is None:
        return True
    if isinstance(component, (list, tuple, np.ndarray)) and np.size(component) == 0:
        return True
    return False


def _extend_prefix(component: Any) -> bool:
    return isinstance(component, str) and component != "" and "extend".startswith(component)


def _coerce_component(component: Any, integer: bool) -> Any:
    if _component_empty(component):
        return None
    if isinstance(component, (list, tuple, np.ndarray)):
        flat = np.asarray(component).reshape(-1)
        if flat.size == 1:
            component = flat[0].item()
        else:
            return [_coerce_component(item, integer) for item in flat]
    if _extend_prefix(component):
        return "extend"
    if isinstance(component, str):
        warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=3)
        return np.nan
    if isinstance(component, (bool, np.bool_)):
        component = int(component)
    try:
        number = float(component)
    except (TypeError, ValueError):
        warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=3)
        return np.nan
    if math.isnan(number):
        return np.nan
    if integer:
        return int(math.trunc(number))
    return number


def _assign_fill(values: np.ndarray, slots: np.ndarray, fill: Any) -> np.ndarray:
    if isinstance(fill, list):
        block = np.resize(np.asarray(fill, dtype=float), slots.size)
        values[slots] = block
        return values
    values[slots] = fill
    return values


def _approx(x: np.ndarray, y: np.ndarray, xout: np.ndarray) -> np.ndarray:
    """R ``approx`` linear interpolation, ``rule = 1``, dropping missing knots."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xout = np.asarray(xout, dtype=float)
    keep = ~np.isnan(y)
    x = x[keep]
    y = y[keep]
    if x.size < 2:
        raise ValueError("need at least two non-NA values to interpolate")
    order = np.argsort(x, kind="mergesort")
    x = x[order]
    y = y[order]
    out = np.full(xout.shape, np.nan, dtype=float)
    inside = (xout >= x[0]) & (xout <= x[-1])
    if not np.any(inside):
        return out
    idx = np.searchsorted(x, xout[inside], side="right") - 1
    idx = np.clip(idx, 0, x.size - 2)
    x0 = x[idx]
    x1 = x[idx + 1]
    y0 = y[idx]
    y1 = y[idx + 1]
    span = x1 - x0
    t = np.ones(idx.shape, dtype=float)
    nonzero = span != 0
    t[nonzero] = (xout[inside][nonzero] - x0[nonzero]) / span[nonzero]
    out[inside] = y0 + t * (y1 - y0)
    return out


def _original_fill_length(fill: Any) -> int:
    if fill is None:
        return 0
    if isinstance(fill, (str, bytes)):
        return 1
    if isinstance(fill, (list, tuple, np.ndarray)):
        return len(fill)
    return 1


def na_fill(values: np.ndarray, index: Any, ix: np.ndarray, fill: Any) -> tuple[np.ndarray, Any] | None:
    """``na.fill.zoo`` for one series. ``ix`` is the positions that stay."""
    values = np.array(values, copy=True)
    n = int(values.shape[0])
    mask = np.zeros(n, dtype=bool)
    ix = np.asarray(ix)
    if ix.dtype == bool:
        if ix.size != n:
            raise ValueError("ix length does not match the series")
        mask = ix.copy()
    else:
        if ix.size:
            mask[np.asarray(ix, dtype=int) - 1] = True
    good = np.flatnonzero(mask)
    if good.size == 0:
        if _original_fill_length(fill) == 0:
            return None
        first = _fill_components(fill)[0]
        if isinstance(first, str) and first == "extend":
            return values, index
        number = _coerce_component(first, np.issubdtype(values.dtype, np.integer))
        if isinstance(number, float) and math.isnan(number):
            return values.astype(float), index
        out = np.array(values, dtype=float, copy=True)
        missing = np.isnan(out) if np.issubdtype(out.dtype, np.floating) else np.zeros(n, dtype=bool)
        if np.issubdtype(values.dtype, np.floating):
            missing = np.isnan(values)
            out = values.astype(float, copy=True)
        else:
            out = values.astype(float, copy=True)
            missing = np.isnan(out)
        out[missing] = np.nan if number is None else number
        return out, index
    integer = np.issubdtype(values.dtype, np.integer)
    parts = [_coerce_component(part, integer) for part in _fill_components(fill)]
    if parts[1] == "extend":
        values = values.astype(float, copy=False)
    elif any(isinstance(part, float) and math.isnan(part) for part in parts):
        values = values.astype(float, copy=False)
    wx_min = int(good[0])
    wx_max = int(good[-1])
    if not _component_empty(parts[0]):
        slots = np.arange(0, wx_min)
        if parts[0] == "extend":
            if slots.size:
                values[slots] = values[wx_min]
        elif slots.size:
            values = _assign_fill(values, slots, parts[0])
    if not _component_empty(parts[1]):
        span = np.arange(wx_min, wx_max + 1)
        if parts[1] == "extend":
            values = values.astype(float, copy=False)
            values[span] = _approx(good, values[good], span)
        else:
            holes = (~mask).copy()
            holes[:wx_min] = False
            holes[wx_max + 1 :] = False
            if np.any(holes):
                values = _assign_fill(values, np.flatnonzero(holes), parts[1])
    if not _component_empty(parts[2]):
        slots = np.arange(wx_max + 1, n)
        if parts[2] == "extend":
            if slots.size:
                values[slots] = values[wx_max]
        elif slots.size:
            values = _assign_fill(values, slots, parts[2])
    keep = np.ones(n, dtype=bool)
    if _component_empty(parts[0]):
        keep[:wx_min] = False
    if _component_empty(parts[1]):
        holes = (~mask).copy()
        holes[:wx_min] = False
        holes[wx_max + 1 :] = False
        keep[holes] = False
    if _component_empty(parts[2]):
        keep[wx_max + 1 :] = False
    return values[keep], _take_index(index, keep)


def _rolling_sum(values: np.ndarray, k: int) -> np.ndarray:
    n = int(values.shape[0])
    nwin = n - k + 1
    integer = np.issubdtype(values.dtype, np.integer)
    if integer:
        work = np.asarray(values)
        diff = np.empty(nwin, dtype=np.int64)
        diff[0] = np.sum(work[:k], dtype=np.int64)
        if nwin > 1:
            idx = np.concatenate((np.array([0]), np.arange(0, n - k)))
            diff[1:] = work[k:n].astype(np.int64) - work[idx[1:]].astype(np.int64)
        return np.cumsum(diff)
    work = np.asarray(values, dtype=float)
    diff = np.empty(nwin, dtype=float)
    diff[0] = float(np.sum(work[:k]))
    if nwin > 1:
        idx = np.concatenate((np.array([0]), np.arange(0, n - k)))
        diff[1:] = work[k:n] - work[idx[1:]]
    return np.cumsum(diff)


def _rolling_max(values: np.ndarray, k: int) -> np.ndarray:
    n = int(values.shape[0])
    if k == 1:
        return np.array(values, copy=True)
    work = np.asarray(values, dtype=float)
    rval = np.zeros(n, dtype=float)
    leaving = 0.0
    for i in range(k - 1, n):
        previous = rval[i - 1]
        if math.isnan(leaving) or math.isnan(previous) or leaving == previous:
            window = work[i - k + 1 : i + 1]
            rval[i] = np.nan if np.isnan(window).any() else float(np.max(window))
        else:
            current = work[i]
            rval[i] = current if math.isnan(current) else max(previous, float(current))
        leaving = float(work[i - k + 1])
    return rval[k - 1 :]


def _median_one(window: np.ndarray) -> float:
    work = np.asarray(window, dtype=float)
    if work.size == 0 or np.isnan(work).any():
        return np.nan
    ordered = np.sort(work)
    mid = ordered.size // 2
    if ordered.size % 2:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2.0)


def _rolling_median(values: np.ndarray, k: int) -> np.ndarray:
    work = np.asarray(values, dtype=float)
    nwin = work.size - k + 1
    out = np.empty(nwin, dtype=float)
    for i in range(nwin):
        out[i] = _median_one(work[i : i + k])
    return out


def _recycle_into(values: np.ndarray, n: int) -> np.ndarray:
    if values.size == n:
        return values
    if values.size == 0:
        raise ValueError("replacement has length zero")
    if n % values.size != 0:
        warnings.warn(
            "number of items to replace is not a multiple of replacement length",
            RuntimeWarning,
            stacklevel=4,
        )
    return np.resize(np.asarray(values), n)


def _resolve_pad(fill: Any, na_pad: Any, warn: str) -> tuple[Any, bool]:
    """Return the fill value and whether the caller supplied fill or na.pad."""
    supplied = fill is not _MISSING or na_pad is not _MISSING
    if na_pad is not _MISSING:
        warnings.warn(warn, DeprecationWarning, stacklevel=3)
    else:
        na_pad = False
    if fill is _MISSING:
        fill = np.nan if na_pad else None
    return fill, supplied


def _place(source: Zoo, positions: np.ndarray, rval: np.ndarray, fill: Any) -> Zoo | None:
    n = len(source)
    mask = np.zeros(n, dtype=bool)
    if positions.size:
        mask[np.asarray(positions, dtype=int) - 1] = True
    if _original_fill_length(fill) == 0:
        if not mask.any():
            return None
        order = np.flatnonzero(mask)
        return _copy_zoo(np.asarray(rval), source, _take_index(source.index, order))
    base = np.array(source.data, copy=True)
    if base.ndim != 1:
        base = np.asarray(base).reshape(-1)
    if np.issubdtype(np.asarray(rval).dtype, np.floating) or np.issubdtype(base.dtype, np.floating):
        base = base.astype(float, copy=False)
    base[mask] = np.asarray(rval, dtype=base.dtype)
    filled = na_fill(base, source.index, mask, fill)
    if filled is None:
        return None
    data, index = filled
    return _copy_zoo(data, source, index)


def _reduce_zoo(source: Zoo, k: int, align: str, fill: Any, rval: np.ndarray) -> Zoo | None:
    if len(rval) == 0 and _original_fill_length(fill) == 0:
        return None
    positions = _align_ix(len(source), k, align)
    rval = _recycle_into(np.asarray(rval), int(positions.size))
    return _place(source, positions, rval, fill)


def _column_map(source: Zoo, fn) -> Zoo | None:
    arr = np.asarray(source.data)
    ncol = int(arr.shape[1])
    names = getattr(source, "colnames", None)
    columns = []
    for j in range(ncol):
        col = Zoo(np.array(arr[:, j], copy=True), source.index, source.frequency, source.regular)
        out = fn(col)
        if out is None:
            return None
        columns.append(out)
    stacked = np.column_stack([np.asarray(col.data).reshape(-1) for col in columns])
    stacked = np.asfortranarray(stacked)
    if ncol == 1:
        stacked = stacked.reshape(-1, 1, order="F")
    result = Zoo(stacked, columns[0].index, source.frequency, source.regular)
    if names is not None and len(names) == stacked.shape[1]:
        result.colnames = list(names)
    return result


def _fun_name(fun: Any) -> str:
    return str(getattr(fun, "__name__", ""))


def _r_mean(window: Any, *args: Any, **kwargs: Any) -> float:
    na_rm = bool(kwargs.get("na.rm", kwargs.get("na_rm", False)))
    work = np.asarray(window, dtype=float).reshape(-1)
    if not na_rm and np.isnan(work).any():
        return np.nan
    if na_rm:
        work = work[~np.isnan(work)]
    if work.size == 0:
        return np.nan
    return float(np.sum(work) / work.size)


def _r_sum(window: Any, *args: Any, **kwargs: Any) -> Any:
    na_rm = bool(kwargs.get("na.rm", kwargs.get("na_rm", False)))
    work = np.asarray(window)
    flat = work.reshape(-1)
    if np.issubdtype(flat.dtype, np.floating) and not na_rm and np.isnan(flat).any():
        return np.nan
    if np.issubdtype(flat.dtype, np.floating) and na_rm:
        flat = flat[~np.isnan(flat)]
    if flat.size == 0:
        return 0 if not np.issubdtype(work.dtype, np.floating) else 0.0
    if np.issubdtype(flat.dtype, np.integer):
        return flat.astype(np.int64).sum()
    return float(np.sum(flat, dtype=float))


def _r_max(window: Any, *args: Any, **kwargs: Any) -> float:
    na_rm = bool(kwargs.get("na.rm", kwargs.get("na_rm", False)))
    work = np.asarray(window, dtype=float).reshape(-1)
    if work.size == 0:
        return -math.inf
    if not na_rm and np.isnan(work).any():
        return np.nan
    if na_rm:
        work = work[~np.isnan(work)]
        if work.size == 0:
            return -math.inf
    return float(np.max(work))


def _r_median(window: Any, *args: Any, **kwargs: Any) -> float:
    na_rm = bool(kwargs.get("na.rm", kwargs.get("na_rm", False)))
    work = np.asarray(window, dtype=float).reshape(-1)
    if na_rm:
        work = work[~np.isnan(work)]
    return _median_one(work)


def _normalize_result(value: Any) -> Any:
    if value is None:
        return None
    arr = np.asarray(value)
    if arr.ndim == 2 and arr.shape[0] > 1:
        return np.ravel(arr, order="F")
    return arr


def _bind_rows(rows: list[np.ndarray]) -> np.ndarray:
    sizes = [int(np.asarray(row).size) for row in rows]
    if not sizes:
        return np.array([], dtype=float)
    if max(sizes) <= 1:
        data = [np.asarray(row).reshape(-1)[0] if np.asarray(row).size else np.nan for row in rows]
        return np.asarray(data)
    stacked = [np.atleast_1d(np.asarray(row)).reshape(-1) for row in rows]
    return np.asfortranarray(np.vstack(stacked))


def _window_at(source: Zoo, positions: np.ndarray, core: bool) -> Any:
    arr = np.asarray(source.data)
    if arr.ndim == 2:
        piece = arr[positions, :]
        if not core:
            return Zoo(np.array(piece, copy=True), _take_index(source.index, positions), source.frequency, source.regular)
        if piece.shape[0] == 1:
            return np.array(piece.reshape(-1), copy=True)
        return np.array(piece, copy=True, order="F")
    piece = arr[positions]
    if not core:
        return Zoo(np.array(piece, copy=True), _take_index(source.index, positions), source.frequency, source.regular)
    return np.array(piece, copy=True)


def _apply_one(source: Zoo, width: Any, fun, args: tuple, kwargs: dict, by: Any, fill: Any, supplied: bool, partial: float, align: str, core: bool) -> Zoo | None:
    n = len(source)
    plan = _prepare_offsets(width, n, align, by, partial)
    results: list[Any] = []
    for i, offsets in enumerate(plan):
        if offsets is None:
            results.append(None)
            continue
        pos = (i + 1) + np.asarray(offsets, dtype=int)
        inside = (pos >= 1) & (pos <= n)
        if partial < 0:
            if inside.size and bool(np.all(inside)):
                results.append(_normalize_result(fun(_window_at(source, pos - 1, core), *args, **kwargs)))
            else:
                results.append(None)
        elif int(np.sum(inside)) >= partial:
            keep = pos[inside] - 1
            results.append(_normalize_result(fun(_window_at(source, keep, core), *args, **kwargs)))
        else:
            results.append(None)
    present = [i for i, item in enumerate(results) if item is not None]
    if not supplied:
        if not present:
            return _copy_zoo(np.array([], dtype=float), source, _take_index(source.index, np.zeros(n, dtype=bool)))
        data = _bind_rows([np.asarray(results[i]) for i in present])
        mask = np.zeros(n, dtype=bool)
        mask[present] = True
        return _copy_zoo(data, source, _take_index(source.index, mask))
    if not present and _original_fill_length(fill) == 0:
        return None
    widths = [int(np.asarray(results[i]).size) for i in present] or [1]
    wide = max(widths) > 1
    if not wide:
        values = np.empty(n, dtype=float)
        mask = np.zeros(n, dtype=bool)
        for i, item in enumerate(results):
            if item is None:
                values[i] = np.nan
            else:
                values[i] = np.asarray(item).reshape(-1)[0]
                mask[i] = True
        filled = na_fill(values, source.index, mask, fill)
        if filled is None:
            return None
        data, index = filled
        return _copy_zoo(data, source, index)
    ncol = max(widths)
    mat = np.full((n, ncol), np.nan, dtype=float)
    mask = np.zeros(n, dtype=bool)
    for i, item in enumerate(results):
        if item is None:
            continue
        row = np.atleast_1d(np.asarray(item, dtype=float)).reshape(-1)
        mat[i, : row.size] = row
        mask[i] = True
    kept_cols = []
    index = source.index
    for j in range(ncol):
        filled = na_fill(mat[:, j], source.index, mask, fill)
        if filled is None:
            return None
        column, index = filled
        kept_cols.append(column)
    stacked = np.asfortranarray(np.column_stack(kept_cols))
    return _copy_zoo(stacked, source, index)


def _rollapply_zoo(data: Zoo, width: Any, fun, args: tuple, kwargs: dict, by: Any, by_column: bool, fill: Any, na_pad: Any, partial: Any, align: Any, core: bool) -> Zoo | None:
    if len(data) < 1:
        return data
    fill, supplied = _resolve_pad(fill, na_pad, "na.pad argument is deprecated")
    align_text = _match_arg(align, _ALIGN)
    partial_code = _partial_code(partial)
    scalar_width = not _is_offset_spec(width) and np.atleast_1d(np.asarray(width, dtype=float)).size == 1
    fast = (
        scalar_width
        and by_column
        and np.size(by) == 1
        and float(np.asarray(by).reshape(-1)[0]) == 1.0
        and partial is False
        and not args
        and not kwargs
    )
    name = _fun_name(fun)
    if fast and name == "mean" and not _any_na(data.data):
        return _rollmean_zoo(data, width, fill, _MISSING, align_text)
    if fast and name == "median" and not _any_na(data.data):
        w = float(np.atleast_1d(np.asarray(width, dtype=float)).reshape(-1)[0])
        if w % 2 == 1:
            return _rollmedian_zoo(data, width, fill, _MISSING, align_text)
    if fast and name == "max":
        return _rollmax_zoo(data, width, fill, _MISSING, align_text)
    if by_column and _is_matrix(data):
        def one(col: Zoo) -> Zoo | None:
            return _rollapply_zoo(col, width, fun, args, kwargs, by, True, fill, _MISSING, partial, align_text, core)

        out = _column_map(data, one)
        if out is not None and _is_matrix(data) and np.asarray(data.data).shape[1] == 1:
            out.data = np.asarray(out.data).reshape(-1, 1, order="F")
        return out
    return _apply_one(data, width, fun, args, kwargs, by, fill, supplied, partial_code, align_text, core)


def rollapply(data, width, FUN, *args, by=1, by_column=True, fill=_MISSING, na_pad=_MISSING, partial=False, align="center", coredata=True, **kwargs):
    """Apply ``FUN`` to rolling windows. A plain series returns the values."""
    if _is_zoo(data):
        if len(data) < 1:
            return data
        return _rollapply_zoo(data, width, FUN, args, kwargs, by, by_column, fill, na_pad, partial, align, coredata)
    if _length(data) < 1:
        return data
    out = _rollapply_zoo(_as_zoo(data), width, FUN, args, kwargs, by, by_column, fill, na_pad, partial, align, coredata)
    if out is None:
        return None
    return out.data


def rollapplyr(*args, align="right", **kwargs):
    """``rollapply`` with right alignment."""
    return rollapply(*args, align=align, **kwargs)


def _positive_k(k: Any) -> int:
    width = _trunc_int(np.atleast_1d(np.asarray(k, dtype=float)).reshape(-1)[0])
    if np.atleast_1d(np.asarray(k)).size != 1:
        raise ValueError("'length = 2' in coercion to 'logical(1)'")
    if width < 1:
        raise ValueError("window width must be positive")
    return width


def _rollmean_zoo(x: Zoo, k: Any, fill: Any, na_pad: Any, align: Any, **kwargs: Any) -> Zoo | None:
    if len(x) < 1:
        return x
    fill, _supplied = _resolve_pad(fill, na_pad, "na.pad is deprecated. Use fill.")
    align = _match_arg(align, _ALIGN)
    if _is_matrix(x):
        return _column_map(x, lambda col: _rollmean_zoo(col, k, fill, _MISSING, align, **kwargs))
    width = _positive_k(k)
    values = np.asarray(x.data)
    if values.ndim != 1:
        values = values.reshape(-1)
    if width > len(x) or _any_na(values):
        return _rollapply_zoo(x, width, _r_mean, (), kwargs, 1, True, fill, _MISSING, False, align, True)
    rval = _rolling_sum(values, width) / float(width)
    return _reduce_zoo(x, width, align, fill, rval)


def rollmean(x, k, fill=_MISSING, na_pad=_MISSING, align="center", **kwargs):
    """Rolling mean. A zoo series stays a zoo series; a plain series returns values."""
    if _is_zoo(x):
        return _rollmean_zoo(x, k, fill, na_pad, align, **kwargs)
    return rollmean_default(x, k, fill=fill, na_pad=na_pad, align=align, **kwargs)


def rollmean_default(x, k, fill=_MISSING, na_pad=_MISSING, align="center", **kwargs):
    """``rollmean.default``: values of the rolling mean."""
    if not _is_zoo(x) and _length(x) < 1:
        return x
    if _is_zoo(x) and len(x) < 1:
        return np.array(x.data, copy=True)
    out = _rollmean_zoo(_as_zoo(x), k, fill, na_pad, align, **kwargs)
    if out is None:
        return None
    return out.data


def rollmeanr(*args, align="right", **kwargs):
    """``rollmean`` with right alignment."""
    return rollmean(*args, align=align, **kwargs)


def _rollsum_zoo(x: Zoo, k: Any, fill: Any, na_pad: Any, align: Any, **kwargs: Any) -> Zoo | None:
    if len(x) < 1:
        return x
    fill, _supplied = _resolve_pad(fill, na_pad, "na.pad is deprecated. Use fill.")
    align = _match_arg(align, _ALIGN)
    if _is_matrix(x):
        return _column_map(x, lambda col: _rollsum_zoo(col, k, fill, _MISSING, align, **kwargs))
    width = _positive_k(k)
    values = np.asarray(x.data)
    if values.ndim != 1:
        values = values.reshape(-1)
    if width > len(x) or _any_na(values):
        return _rollapply_zoo(x, width, _r_sum, (), kwargs, 1, True, fill, _MISSING, False, align, True)
    return _reduce_zoo(x, width, align, fill, _rolling_sum(values, width))


def rollsum(x, k, fill=_MISSING, na_pad=_MISSING, align="center", **kwargs):
    """Rolling sum. A zoo series stays a zoo series; a plain series returns values."""
    if _is_zoo(x):
        return _rollsum_zoo(x, k, fill, na_pad, align, **kwargs)
    return rollsum_default(x, k, fill=fill, na_pad=na_pad, align=align, **kwargs)


def rollsum_default(x, k, fill=_MISSING, na_pad=_MISSING, align="center", **kwargs):
    """``rollsum.default``: values of the rolling sum."""
    if not _is_zoo(x) and _length(x) < 1:
        return x
    if _is_zoo(x) and len(x) < 1:
        return np.array(x.data, copy=True)
    out = _rollsum_zoo(_as_zoo(x), k, fill, na_pad, align, **kwargs)
    if out is None:
        return None
    return out.data


def rollsumr(*args, align="right", **kwargs):
    """``rollsum`` with right alignment."""
    return rollsum(*args, align=align, **kwargs)


def _rollmax_zoo(x: Zoo, k: Any, fill: Any, na_pad: Any, align: Any, **kwargs: Any) -> Zoo | None:
    if len(x) < 1:
        return x
    fill, _supplied = _resolve_pad(fill, na_pad, "na.pad is deprecated. Use fill.")
    align = _match_arg(align, _ALIGN)
    if _is_matrix(x):
        return _column_map(x, lambda col: _rollmax_zoo(col, k, fill, _MISSING, align, **kwargs))
    width = _positive_k(k)
    values = np.asarray(x.data)
    if values.ndim != 1:
        values = values.reshape(-1)
    if width > len(x):
        return _rollapply_zoo(x, width, _r_max, (), kwargs, 1, True, fill, _MISSING, False, align, True)
    return _reduce_zoo(x, width, align, fill, _rolling_max(values, width))


def rollmax(x, k, fill=_MISSING, na_pad=_MISSING, align="center", **kwargs):
    """Rolling maximum. A zoo series stays a zoo series; a plain series returns values."""
    if _is_zoo(x):
        return _rollmax_zoo(x, k, fill, na_pad, align, **kwargs)
    return rollmax_default(x, k, fill=fill, na_pad=na_pad, align=align, **kwargs)


def rollmax_default(x, k, fill=_MISSING, na_pad=_MISSING, align="center", **kwargs):
    """``rollmax.default``: values of the rolling maximum."""
    if not _is_zoo(x) and _length(x) < 1:
        return x
    if _is_zoo(x) and len(x) < 1:
        return np.array(x.data, copy=True)
    out = _rollmax_zoo(_as_zoo(x), k, fill, na_pad, align, **kwargs)
    if out is None:
        return None
    return out.data


def rollmaxr(*args, align="right", **kwargs):
    """``rollmax`` with right alignment."""
    return rollmax(*args, align=align, **kwargs)


def _rollmedian_zoo(x: Zoo, k: Any, fill: Any, na_pad: Any, align: Any, **kwargs: Any) -> Zoo | None:
    if len(x) < 1:
        return x
    fill, _supplied = _resolve_pad(fill, na_pad, "na.pad is deprecated. Use fill.")
    align = _match_arg(align, _ALIGN)
    if _is_matrix(x):
        return _column_map(x, lambda col: _rollmedian_zoo(col, k, fill, _MISSING, align, **kwargs))
    width = _positive_k(k)
    values = np.asarray(x.data)
    if values.ndim != 1:
        values = values.reshape(-1)
    if width > len(x) or _any_na(values):
        return _rollapply_zoo(x, width, _r_median, (), kwargs, 1, True, fill, _MISSING, False, align, True)
    for key in ("endrule", "algorithm", "print.level", "print_level"):
        kwargs.pop(key, None)
    if kwargs:
        raise TypeError("unused argument")
    used = width
    if width % 2 == 0:
        used = width + 1
        warnings.warn(f"'k' must be odd!  Changing 'k' to {used}", RuntimeWarning, stacklevel=3)
    medians = _rolling_median(values, used)
    return _reduce_zoo(x, width, align, fill, medians)


def rollmedian(x, k, fill=_MISSING, na_pad=_MISSING, align="center", **kwargs):
    """Rolling median. ``k`` is odd. A plain series returns values."""
    if _is_zoo(x):
        return _rollmedian_zoo(x, k, fill, na_pad, align, **kwargs)
    return rollmedian_default(x, k, fill=fill, na_pad=na_pad, align=align, **kwargs)


def rollmedian_default(x, k, fill=_MISSING, na_pad=_MISSING, align="center", **kwargs):
    """``rollmedian.default``: values of the rolling median."""
    if not _is_zoo(x) and _length(x) < 1:
        return x
    if _is_zoo(x) and len(x) < 1:
        return np.array(x.data, copy=True)
    out = _rollmedian_zoo(_as_zoo(x), k, fill, na_pad, align, **kwargs)
    if out is None:
        return None
    return out.data


def rollmedianr(*args, align="right", **kwargs):
    """``rollmedian`` with right alignment."""
    return rollmedian(*args, align=align, **kwargs)
