"""Coercion to zoo and zooreg.

as.zoo for a vector, matrix, data frame, factor, ts, or zoo. Other classes
that zoo knows about (xts, tis, timeSeries, fts, coda, chron) raise.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from zoo.series import Zoo

BAD_X = "\u201cx\u201d : attempt to define invalid zoo object"
_FREQ_WARN = (
    "\u201corder.by\u201d and \u201cfrequency\u201d do not match: \u201cfrequency\u201d ignored"
)
_DUP_WARN = (
    "some methods for \u201czoo\u201d objects do not work if the index entries in "
    "\u2018order.by\u2019 are not unique"
)
_IRREG = "\u2018x\u2019 does not have an underlying regularity"
_ORDER_MULTI = 'formal argument "order.by" matched by multiple actual arguments'
_FOREIGN = {
    "fts",
    "irts",
    "its",
    "mcmc",
    "tis",
    "xts",
    "timeSeries",
    "timeDate",
    "chron",
    "coda",
}

NA_INT = np.int32(-2147483648)
NA_LGL = np.int8(-128)


class RArray(np.ndarray):
    """Array plus the attributes zoo keeps on core data."""

    def __array_finalize__(self, obj: Any) -> None:
        if obj is None:
            return
        self.r_mode = getattr(obj, "r_mode", None)
        self.columns = getattr(obj, "columns", None)
        self.rows = getattr(obj, "rows", None)
        self.levels = getattr(obj, "levels", None)
        self.ordered = bool(getattr(obj, "ordered", False))


class DataFrame:
    """Column-oriented stand-in for an R data.frame. A dict is accepted too."""

    def __init__(self, columns: dict[str, Any] | None = None, **kwargs: Any) -> None:
        self.columns = dict(columns or {})
        self.columns.update(kwargs)


class Ts:
    """A base ts: data, start, end, and frequency. Start may be c(year, period)."""

    r_class = "ts"

    def __init__(
        self,
        data: Any,
        start: Any = 1,
        end: Any = None,
        frequency: float = 1,
        columns: Any = None,
    ) -> None:
        self.frequency = float(frequency)
        self.data = ingest(data)
        if self.data.ndim == 2:
            names = columns if columns is not None else getattr(self.data, "columns", None)
            if names is None:
                names = tuple(f"Series {i}" for i in range(1, self.data.shape[1] + 1))
            self.data.columns = tuple(names)
        self.start = ts_endpoint(start, self.frequency)
        n = _nrow(self.data)
        if end is None:
            self.end = self.start + (n - 1) / self.frequency if n else self.start
        else:
            self.end = ts_endpoint(end, self.frequency)


def ts_endpoint(value: Any, frequency: float) -> float:
    if isinstance(value, (list, tuple, np.ndarray)):
        arr = np.asarray(value, dtype=np.float64).reshape(-1)
        if arr.size > 1:
            return float(arr[0] + (arr[1] - 1.0) / frequency)
        if arr.size == 1:
            return float(arr[0])
        raise ValueError("invalid ts time")
    return float(value)


def r_mod(a: Any, b: Any) -> Any:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return a - b * np.floor(a / b)


def ts_time(x: Ts, offset: float = 0.0, ts_eps: float = 1e-5) -> np.ndarray:
    n = _nrow(x.data)
    start = float(x.start)
    end = float(x.end)
    freq = float(x.frequency)
    if n <= 0:
        y = np.array([], dtype=np.float64)
    elif n == 1:
        y = np.array([start], dtype=np.float64)
    else:
        y = start + np.arange(n, dtype=np.float64) * ((end - start) / (n - 1))
    y = y + float(offset) / freq
    if ts_eps > 0 and y.size:
        rounded = np.round(y)
        near = np.abs(rounded - y) < ts_eps
        y = np.where(near, rounded, y)
    return y


def ts_cycle(x: Ts) -> np.ndarray:
    n = _nrow(x.data)
    freq = float(x.frequency)
    m = float(np.round(float(r_mod(x.start, 1.0)) * freq))
    return r_mod(np.arange(1, n + 1, dtype=np.float64) + m - 1.0, freq) + 1.0


def r_all_equal(target: Any, current: Any, tolerance: float | None = None) -> bool:
    """True when R's all.equal on plain numbers returns TRUE."""
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


def _nrow(data: Any) -> int:
    arr = np.asarray(data)
    if arr.ndim == 0:
        return 1
    return int(arr.shape[0])


def _wrap(
    values: Any,
    r_mode: str,
    columns: Any = None,
    rows: Any = None,
    levels: Any = None,
    ordered: bool = False,
    order: str = "C",
) -> RArray:
    base = np.array(values, order="F" if np.ndim(values) == 2 else order, copy=True)
    obj = base.view(RArray)
    obj.r_mode = r_mode
    obj.columns = None if columns is None else tuple(columns)
    obj.rows = None if rows is None else tuple(rows)
    obj.levels = None if levels is None else tuple(levels)
    obj.ordered = bool(ordered)
    return obj


def logical_na() -> RArray:
    return _wrap(np.array([NA_LGL], dtype=np.int8), "logical")


def as_r_integer(values: Any) -> np.ndarray:
    rounded = np.asarray(values, dtype=np.float64).reshape(-1)
    out = np.empty(rounded.shape, dtype=np.int32)
    for i, value in enumerate(rounded):
        if not np.isfinite(value) or value < -2147483647 or value > 2147483647:
            out[i] = NA_INT
        else:
            out[i] = int(value)
    return out


def factor(values: Any, levels: Any = None, ordered: bool = False) -> RArray:
    seq = list(values)
    if levels is None:
        found: list[Any] = []
        for value in seq:
            if value is not None and value not in found:
                found.append(value)
        levels = found
    levels = list(levels)
    codes = np.empty(len(seq), dtype=np.int32)
    for i, value in enumerate(seq):
        if value is None:
            codes[i] = NA_INT
        else:
            try:
                codes[i] = levels.index(value) + 1
            except ValueError:
                codes[i] = NA_INT
    return _wrap(codes, "factor", levels=levels, ordered=ordered)


def ordered(values: Any, levels: Any = None) -> RArray:
    return factor(values, levels=levels, ordered=True)


def _is_bool(value: Any) -> bool:
    return isinstance(value, (bool, np.bool_))


def _is_int(value: Any) -> bool:
    return isinstance(value, (int, np.integer)) and not _is_bool(value)


def _double_from(seq: list[Any]) -> RArray:
    from zoo.as_date import R_NA, na_bit

    out = np.empty(len(seq), dtype=np.float64)
    for i, value in enumerate(seq):
        if value is None:
            out[i] = R_NA
        elif isinstance(value, float) and na_bit(value):
            out[i] = value
        else:
            out[i] = value
    return _wrap(out, "double")


def _from_sequence(seq: list[Any]) -> RArray:
    if not seq:
        return _wrap(np.array([], dtype=np.float64), "double")
    if any(isinstance(v, (list, tuple, dict, np.ndarray)) for v in seq):
        raise ValueError(BAD_X)
    if all(v is None or isinstance(v, str) for v in seq):
        return _wrap(np.array(seq, dtype=object), "character")
    if all(_is_bool(v) or v is None for v in seq):
        out = np.empty(len(seq), dtype=np.int8)
        for i, value in enumerate(seq):
            if value is None:
                out[i] = NA_LGL
            else:
                out[i] = 1 if value else 0
        return _wrap(out, "logical")
    if all(v is None or _is_int(v) or isinstance(v, (float, np.floating)) for v in seq):
        return _double_from(seq)
    raise ValueError(BAD_X)


def _from_ndarray(x: np.ndarray) -> RArray:
    if isinstance(x, RArray) and x.r_mode:
        return _wrap(
            np.asarray(x),
            x.r_mode,
            columns=x.columns,
            rows=x.rows,
            levels=x.levels,
            ordered=x.ordered,
        )
    if x.ndim > 2:
        raise ValueError(BAD_X)
    if x.dtype == bool:
        out = np.where(x, np.int8(1), np.int8(0)).astype(np.int8)
        return _wrap(out, "logical")
    if x.dtype == object:
        return _from_sequence(x.reshape(-1).tolist()) if x.ndim == 1 else _wrap(x, "character")
    if np.issubdtype(x.dtype, np.integer):
        return _wrap(np.array(x, dtype=np.int32, copy=True), "integer")
    if np.issubdtype(x.dtype, np.floating):
        return _wrap(np.array(x, dtype=np.float64, copy=True), "double")
    if np.issubdtype(x.dtype, np.complexfloating):
        return _wrap(np.array(x, dtype=np.complex128, copy=True), "complex")
    if x.dtype.kind in "SU":
        return _wrap(np.array(x, dtype=object), "character")
    if x.dtype == np.uint8:
        return _wrap(np.array(x, dtype=np.uint8, copy=True), "raw")
    raise ValueError(BAD_X)


def ingest(x: Any) -> RArray:
    if isinstance(x, DataFrame):
        return _frame_matrix(x.columns)
    if isinstance(x, dict):
        return _frame_matrix(x)
    if isinstance(x, RArray):
        return _from_ndarray(x)
    if isinstance(x, np.ndarray):
        return _from_ndarray(x)
    if isinstance(x, str):
        return _wrap(np.array([x], dtype=object), "character")
    if isinstance(x, (list, tuple)):
        return _from_sequence(list(x))
    if _is_bool(x):
        return _wrap(np.array([1 if x else 0], dtype=np.int8), "logical")
    if isinstance(x, np.integer):
        return _wrap(np.array([x], dtype=np.int32), "integer")
    if isinstance(x, (int, float, np.floating)):
        return _double_from([x])
    if x is None:
        return _wrap(np.array([], dtype=np.float64), "double")
    raise ValueError(BAD_X)


def _as_character_list(col: RArray) -> list[Any]:
    mode = col.r_mode
    if mode == "factor":
        levels = list(col.levels or ())
        out = []
        for code in np.asarray(col).reshape(-1):
            if int(code) == int(NA_INT):
                out.append(None)
            else:
                out.append(levels[int(code) - 1])
        return out
    if mode == "logical":
        out = []
        for value in np.asarray(col).reshape(-1):
            if int(value) == int(NA_LGL):
                out.append(None)
            else:
                out.append("TRUE" if int(value) else "FALSE")
        return out
    if mode == "integer":
        out = []
        for value in np.asarray(col).reshape(-1):
            if int(value) == int(NA_INT):
                out.append(None)
            else:
                out.append(str(int(value)))
        return out
    if mode == "character":
        return [None if value is None else str(value) for value in np.asarray(col).reshape(-1)]
    out = []
    from zoo.as_date import na_bit

    for value in np.asarray(col, dtype=np.float64).reshape(-1):
        if na_bit(value):
            out.append(None)
        elif math.isnan(value):
            out.append("NaN")
        elif math.isinf(value):
            out.append("Inf" if value > 0 else "-Inf")
        elif value == math.trunc(value) and abs(value) < 1e16:
            out.append(str(int(math.trunc(value))))
        else:
            out.append(format(float(value), ".15g"))
    return out


def _cast_column(col: RArray, mode: str) -> np.ndarray:
    from zoo.as_date import R_NA, is_r_na

    n = col.shape[0]
    if mode == "logical":
        return np.array(col, dtype=np.int8, copy=True)
    if mode == "integer":
        out = np.empty(n, dtype=np.int32)
        if col.r_mode == "logical":
            src = np.asarray(col)
            out[:] = src
            out[src == NA_LGL] = NA_INT
            return out
        src = np.asarray(col)
        out[:] = src
        return out
    out = np.empty(n, dtype=np.float64)
    if col.r_mode == "logical":
        src = np.asarray(col)
        out[:] = src
        out[src == NA_LGL] = R_NA
        return out
    if col.r_mode == "integer":
        src = np.asarray(col)
        out[:] = src
        out[src == NA_INT] = R_NA
        return out
    src = np.asarray(col, dtype=np.float64)
    out[:] = src
    na = is_r_na(src)
    if np.any(na):
        out[na] = src[na]
    return out


def _frame_matrix(columns: dict[str, Any]) -> RArray:
    names = list(columns)
    ingested = [ingest(columns[name]) for name in names]
    if not ingested:
        out = _wrap(np.empty((0, 0), dtype=np.float64), "double", columns=())
        return out
    nrow = ingested[0].shape[0]
    if any(col.shape[0] != nrow for col in ingested):
        raise ValueError("arguments imply differing number of rows")
    modes = [col.r_mode for col in ingested]
    if any(mode in {"character", "factor", "complex", "raw"} for mode in modes):
        mat = np.empty((nrow, len(names)), dtype=object, order="F")
        for j, col in enumerate(ingested):
            mat[:, j] = _as_character_list(col)
        return _wrap(mat, "character", columns=names)
    if any(mode == "double" for mode in modes):
        dtype: Any = np.float64
        mode = "double"
    elif any(mode == "integer" for mode in modes):
        dtype = np.int32
        mode = "integer"
    else:
        dtype = np.int8
        mode = "logical"
    mat = np.empty((nrow, len(names)), dtype=dtype, order="F")
    for j, col in enumerate(ingested):
        mat[:, j] = _cast_column(col, mode)
    return _wrap(mat, mode, columns=names)


def _factor_labels(data: RArray) -> list[Any]:
    levels = list(data.levels or ())
    labels = []
    for code in np.asarray(data).reshape(-1):
        if int(code) == int(NA_INT):
            labels.append(None)
        else:
            labels.append(levels[int(code) - 1])
    return labels


def _take(data: RArray, idx: np.ndarray) -> RArray:
    idx = np.asarray(idx, dtype=int)
    out = data[idx] if data.ndim == 1 else data[idx, :]
    out.r_mode = data.r_mode
    out.columns = data.columns
    out.levels = data.levels
    out.ordered = data.ordered
    if data.rows is not None:
        out.rows = tuple(data.rows[i] for i in idx)
    else:
        out.rows = None
    return out


def _align(data: RArray, n: int, order: np.ndarray) -> RArray:
    m = _nrow(data)
    identity = n == m and np.array_equal(order, np.arange(n))
    if identity:
        return data
    if data.r_mode == "factor":
        labels = _factor_labels(data)
        if m == 0:
            recycled = [None] * n
        else:
            recycled = [labels[i % m] for i in range(n)]
        reordered = [recycled[i] for i in order] if n else []
        return factor(reordered, levels=data.levels, ordered=data.ordered)
    if n == 0:
        return _take(data, np.array([], dtype=int))
    if m == 0:
        raise ValueError(BAD_X)
    positions = (np.arange(n) % m)[order]
    return _take(data, positions)


def _has_duplicate(index: Any) -> bool:
    arr = np.asarray(index)
    if arr.size <= 1:
        return False
    if np.issubdtype(arr.dtype, np.floating):
        vals = np.asarray(arr, dtype=np.float64)
        nan = np.isnan(vals)
        if int(np.sum(nan)) > 1:
            return True
        finite = vals[~nan]
        finite = np.where(finite == 0, 0.0, finite)
        return int(np.unique(finite).size) < int(finite.size)
    if np.issubdtype(arr.dtype, np.integer):
        return int(np.unique(arr).size) < int(arr.size)
    return len(set(arr.tolist())) < int(arr.size)


def _permute(index: Any) -> tuple[np.ndarray, Any]:
    n = int(np.asarray(index).shape[0])
    if n == 0:
        return np.array([], dtype=int), index
    if isinstance(index, np.ndarray) and np.issubdtype(index.dtype, np.floating):
        vals = np.asarray(index, dtype=np.float64)
        if np.any(np.isnan(vals)):
            na = np.isnan(vals)
            key = np.where(na, 0.0, vals)
            order = np.lexsort((np.arange(n), key, na.astype(np.int8)))
            return order, index[order]
    if isinstance(index, np.ndarray) and np.issubdtype(index.dtype, np.integer):
        if np.any(np.asarray(index) == NA_INT):
            na = np.asarray(index) == NA_INT
            key = np.where(na, 0, np.asarray(index)).astype(np.float64)
            order = np.lexsort((np.arange(n), key, na.astype(np.int8)))
            return order, index[order]
    order = np.argsort(np.asarray(index), kind="stable")
    if np.array_equal(order, np.arange(n)):
        return order, index
    return order, index[order]


def _index_kind(index: Any) -> str:
    name = type(index).__name__
    if name in {"Yearqtr", "Yearmon", "RDate"}:
        return name
    if isinstance(index, np.ndarray) and np.issubdtype(index.dtype, np.integer):
        return "integer"
    return "numeric"


def _normalize_index(order_by: Any, n_default: int) -> Any:
    if order_by is None:
        return np.arange(1, n_default + 1, dtype=np.int32)
    name = type(order_by).__name__
    if name in {"Yearmon", "Yearqtr", "RDate"}:
        return order_by
    import datetime as _dt

    if isinstance(order_by, _dt.date) and not isinstance(order_by, _dt.datetime):
        from zoo.as_date import RDate

        return RDate([order_by.toordinal() - 719163])
    if isinstance(order_by, np.ndarray):
        if np.issubdtype(order_by.dtype, np.integer):
            return np.array(order_by, dtype=np.int32, copy=True).reshape(-1)
        if np.issubdtype(order_by.dtype, np.floating):
            return np.array(order_by, dtype=np.float64, copy=True).reshape(-1)
        return np.array(order_by, copy=True).reshape(-1)
    if isinstance(order_by, (list, tuple)):
        if order_by and isinstance(order_by[0], str):
            return np.array(order_by, dtype=object)
        if any(isinstance(v, np.integer) for v in order_by) and all(
            isinstance(v, (int, np.integer)) and not _is_bool(v) for v in order_by
        ):
            return np.array(order_by, dtype=np.int32)
        return np.array(order_by, dtype=np.float64)
    if isinstance(order_by, np.integer):
        return np.array([order_by], dtype=np.int32)
    if isinstance(order_by, (int, float, np.floating)) and not _is_bool(order_by):
        return np.array([order_by], dtype=np.float64)
    raise ValueError(BAD_X)


def frequency_infer(index: Any) -> float | None:
    values = np.asarray(index, dtype=np.float64).reshape(-1)
    if values.size < 2:
        return None
    delta = np.diff(values)
    if np.any(np.isnan(delta)):
        return None
    uniq: list[float] = []
    for value in delta:
        if not any(float(value) == seen for seen in uniq):
            uniq.append(float(value))
    delta_u = np.array(uniq, dtype=np.float64)
    min_d = float(np.min(delta_u))
    if r_all_equal(delta_u / min_d, np.round(delta_u / min_d)):
        freq = 1.0 / min_d
    elif r_all_equal(delta_u, np.round(delta_u)):
        freq = 1.0 / _gcd_vec(delta_u)
    else:
        return None
    if freq > 1 and r_all_equal(freq, round(freq)):
        freq = float(round(freq))
    return float(freq)


def _gcd_scalar(a: float, b: float) -> float:
    for _ in range(256):
        if b == 0 or a == b or math.isnan(b):
            return a
        a, b = b, a - b * math.floor(a / b)
    return a


def _gcd_vec(x: Any) -> float:
    vals = [float(v) for v in np.asarray(x, dtype=np.float64).reshape(-1)]
    if len(vals) < 2:
        vals = vals + [0.0]
    if len(vals) < 3:
        return _gcd_scalar(vals[0], vals[1])
    reduced = [_gcd_scalar(vals[i], vals[i + 1]) for i in range(len(vals) - 1)]
    return _gcd_vec(reduced)


def frequency_set_zoo(index: Any, value: float) -> float:
    value = float(value)
    delta = np.diff(np.asarray(index, dtype=np.float64).reshape(-1))
    if np.any(np.isnan(delta)):
        ok = False
    elif delta.size < 1:
        ok = True
    else:
        ok = r_all_equal(delta * value, np.round(delta * value))
    if not ok:
        raise ValueError("freqOK is not TRUE")
    if value > 1 and r_all_equal(value, round(value)):
        value = float(round(value))
    return value


def frequency_set_zooreg(index: Any, value: float) -> float:
    value = float(value)
    delta = np.diff(np.asarray(index, dtype=np.float64).reshape(-1))
    if not r_all_equal(delta * value, np.round(delta * value)):
        raise ValueError(
            "identical(all.equal(delta * value, round(delta * value)), TRUE) is not TRUE"
        )
    return value


def _empty_double() -> RArray:
    return _wrap(np.array([], dtype=np.float64), "double")


def zoo_create(
    x: Any,
    order_by: Any = None,
    frequency: float | None = None,
    calendar: bool = True,
) -> Zoo:
    """R's zoo(). A matrix whose dimensions sum to less than 1 becomes numeric(0)."""
    import warnings

    if isinstance(x, RArray):
        data = x
    else:
        data = ingest(x)
    if data.ndim == 2 and (data.shape[0] + data.shape[1]) < 1:
        data = _empty_double()
    index = _normalize_index(order_by, _nrow(data))
    if _has_duplicate(index):
        warnings.warn(_DUP_WARN, UserWarning, stacklevel=2)
    order, index = _permute(index)
    data = _align(data, int(np.asarray(index).shape[0]), order)

    if frequency is not None:
        frequency = float(frequency)
        delta = np.diff(np.asarray(index, dtype=np.float64).reshape(-1))
        if np.any(np.isnan(delta)):
            freq_ok = False
        elif delta.size < 1:
            freq_ok = True
        else:
            freq_ok = r_all_equal(delta * frequency, np.round(delta * frequency))
        if not freq_ok:
            warnings.warn(_FREQ_WARN, UserWarning, stacklevel=2)
            frequency = None
        elif frequency > 1 and r_all_equal(frequency, round(frequency)):
            frequency = float(round(frequency))
        kind = _index_kind(index)
        # R parses `&&` before `|`, so an integer index enters even after frequency was dropped.
        entered = ((frequency is not None) and kind == "numeric") or kind == "integer"
        if entered:
            if frequency is None:
                if calendar:
                    raise ValueError("missing value where TRUE/FALSE needed")
            else:
                snapped = np.floor(frequency * np.asarray(index, dtype=np.float64) + 0.0001) / frequency
                if r_all_equal(snapped, np.asarray(index, dtype=np.float64)):
                    index = snapped
                    kind = "numeric"
                if calendar and frequency in (4, 12) and kind in {"numeric", "integer"}:
                    from zoo.zooreg import as_yearmon, as_yearqtr

                    index = as_yearqtr(index) if frequency == 4 else as_yearmon(index)
    return Zoo(data, index, frequency=frequency, regular=frequency is not None)


def _foreign(x: Any) -> str | None:
    name = type(x).__name__
    r_class = getattr(x, "r_class", None)
    if name in _FOREIGN:
        return name
    if isinstance(r_class, str) and r_class in _FOREIGN:
        return r_class
    return None


def as_zoo_default(x: Any, frequency: float | None = None, calendar: bool = True, **kwargs: Any) -> Zoo:
    if "order_by" in kwargs:
        raise ValueError(_ORDER_MULTI)
    if kwargs:
        name = next(iter(kwargs))
        raise TypeError(f"unused argument ({name})")
    return zoo_create(x, order_by=None, frequency=frequency, calendar=calendar)


def as_zoo(
    x: Any,
    frequency: float | None = None,
    calendar: bool = True,
    **kwargs: Any,
) -> Zoo:
    foreign = _foreign(x)
    if foreign:
        raise TypeError(f"as.zoo method for class '{foreign}' is not available")
    order_by = kwargs.pop("order_by", None)
    passed_order = "order_by" in kwargs or order_by is not None
    # Distinguishing a missing order.by from NULL: None means "not supplied".
    if isinstance(x, Zoo):
        if kwargs:
            name = next(iter(kwargs))
            raise TypeError(f"unused argument ({name})")
        return _as_zoo_zoo(x)
    if isinstance(x, Ts):
        return _as_zoo_ts(x, frequency=frequency, calendar=calendar, order_by=order_by, **kwargs)
    if isinstance(x, (DataFrame, dict)) or (
        isinstance(x, RArray) and x.ndim == 2
    ) or (isinstance(x, np.ndarray) and x.ndim == 2) or (
        isinstance(x, RArray) and getattr(x, "r_mode", None) == "factor"
    ):
        if kwargs:
            name = next(iter(kwargs))
            raise TypeError(f"unused argument ({name})")
        return zoo_create(
            x,
            order_by=order_by if passed_order else None,
            frequency=frequency,
            calendar=calendar,
        )
    if passed_order:
        raise ValueError(_ORDER_MULTI)
    return as_zoo_default(x, frequency=frequency, calendar=calendar, **kwargs)


def _as_zoo_zoo(x: Zoo) -> Zoo:
    if not x.regular:
        return x
    return Zoo(x.data, x.index, frequency=None, regular=False)


def _as_zoo_ts(x: Ts, frequency: float | None = None, calendar: bool = True, order_by: Any = None, **kwargs: Any) -> Zoo:
    from zoo.zooreg import zooreg

    freq = x.frequency if frequency is None else frequency
    extra: dict[str, Any] = {"calendar": calendar}
    if order_by is not None:
        extra["order_by"] = order_by
    if "deltat" in kwargs:
        extra["deltat"] = kwargs.pop("deltat")
    if "ts_eps" in kwargs:
        extra["ts_eps"] = kwargs.pop("ts_eps")
    if kwargs:
        name = next(iter(kwargs))
        raise TypeError(f"unused argument ({name})")
    return zooreg(x.data, start=x.start, end=x.end, frequency=freq, **extra)


def as_zooreg(x: Any, frequency: float | None = None, **kwargs: Any) -> Zoo:
    if isinstance(x, Ts):
        return _as_zoo_ts(x, frequency=frequency, **kwargs)
    if isinstance(x, Zoo):
        if kwargs:
            name = next(iter(kwargs))
            raise TypeError(f"unused argument ({name})")
        return _as_zooreg_zoo(x, frequency=frequency)
    return as_zooreg_default(x, frequency=frequency, **kwargs)


def as_zooreg_default(x: Any, frequency: float | None = None, **kwargs: Any) -> Zoo:
    converted = as_zoo(x, **kwargs)
    return as_zooreg(converted, frequency=frequency)


def _as_zooreg_zoo(x: Zoo, frequency: float | None = None) -> Zoo:
    import warnings

    if frequency is not None:
        if x.regular:
            value = frequency_set_zooreg(x.index, frequency)
        else:
            value = frequency_set_zoo(x.index, frequency)
        return Zoo(x.data, x.index, frequency=value, regular=True)
    if x.regular and x.frequency is not None:
        return Zoo(x.data, x.index, frequency=x.frequency, regular=True)
    inferred = frequency_infer(x.index)
    if inferred is not None:
        return Zoo(x.data, x.index, frequency=inferred, regular=True)
    warnings.warn(_IRREG, UserWarning, stacklevel=2)
    from zoo.zooreg import zooreg

    return zooreg(x.data)
