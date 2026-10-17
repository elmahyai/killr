"""Scale estimates from sequential differences, ported from matrixStats 1.5.0.

``varDiff``, ``sdDiff``, ``madDiff``, and ``iqrDiff`` follow ``R/varDiff.R``.
Each one subsets with base R ``[``, optionally drops missing values, then
calls ``diff2`` when ``diff > 0``. The variance is divided by ``2 ** diff``.
The standard deviation, MAD, and IQR are divided by ``sqrt(2) ** diff``.
That divisor is the original ``diff``. ``diff2`` still truncates its order
with ``as.integer``, so ``diff = 1.9`` is a first difference divided by
``2 ** 1.9``.

``iqrDiff`` calls the type-7 quantile, which is what ``stats::IQR`` uses.
It does not call the matrixStats ``iqr`` routine. ``madDiff`` applies the
``stats::mad`` constant, default ``1.4826``. Row and column wrappers follow
``apply`` along axis 0 or axis 1. ``rows`` and ``cols`` are 1-based, and
``None`` means every row or column.
"""

from __future__ import annotations

import math

import numpy as np

from matrixstats._values import as_logical
from matrixstats.anymissing import anyMissing
from matrixstats.diff2 import diff2

NA_INTEGER = -2147483648

__all__ = [
    "varDiff",
    "sdDiff",
    "madDiff",
    "iqrDiff",
    "rowVarDiffs",
    "colVarDiffs",
    "rowSdDiffs",
    "colSdDiffs",
    "rowMadDiffs",
    "colMadDiffs",
    "rowIQRDiffs",
    "colIQRDiffs",
]


def varDiff(x, idxs=None, na_rm=False, diff=1, trim=0, **_ignored):
    """Sample variance of lagged differences, divided by ``2 ** diff``.

    Mirrors ``matrixStats::varDiff``. ``idxs`` is 1-based; ``None`` selects
    every element. ``diff`` and ``trim`` default to 1 and 0.
    """
    return _vector(x, idxs, na_rm, diff, trim, "var")


def sdDiff(x, idxs=None, na_rm=False, diff=1, trim=0, **_ignored):
    """Sample standard deviation of lagged differences, divided by ``sqrt(2) ** diff``.

    Mirrors ``matrixStats::sdDiff``.
    """
    return _vector(x, idxs, na_rm, diff, trim, "sd")


def madDiff(
    x,
    idxs=None,
    na_rm=False,
    diff=1,
    trim=0,
    constant=1.4826,
    low=False,
    high=False,
    center=None,
):
    """Median absolute deviation of lagged differences, divided by ``sqrt(2) ** diff``.

    Mirrors ``matrixStats::madDiff``. ``constant`` is the normal-consistency
    factor passed to ``stats::mad``. ``low`` and ``high`` select one of the
    two central deviations when the count is even.
    """
    return _vector(
        x,
        idxs,
        na_rm,
        diff,
        trim,
        "mad",
        constant=constant,
        low=low,
        high=high,
        center=center,
    )


def iqrDiff(x, idxs=None, na_rm=False, diff=1, trim=0, type=7, fuzz=None):
    """Interquartile range of lagged differences, divided by ``sqrt(2) ** diff``.

    Mirrors ``matrixStats::iqrDiff``. The quartiles are ``stats::quantile``
    with the given ``type`` (default 7, the same type ``stats::IQR`` uses).
    No extra normal-consistency constant is applied.
    """
    return _vector(
        x, idxs, na_rm, diff, trim, "iqr", qtype=type, fuzz=fuzz
    )


def rowVarDiffs(
    x, rows=None, cols=None, na_rm=False, diff=1, trim=0, use_names=True, **_ignored
):
    """``varDiff`` of each row. Axis 0 is rows and axis 1 is columns."""
    return _margin(x, rows, cols, na_rm, diff, trim, use_names, 0, "var")


def colVarDiffs(
    x, rows=None, cols=None, na_rm=False, diff=1, trim=0, use_names=True, **_ignored
):
    """``varDiff`` of each column."""
    return _margin(x, rows, cols, na_rm, diff, trim, use_names, 1, "var")


def rowSdDiffs(
    x, rows=None, cols=None, na_rm=False, diff=1, trim=0, use_names=True, **_ignored
):
    """``sdDiff`` of each row."""
    return _margin(x, rows, cols, na_rm, diff, trim, use_names, 0, "sd")


def colSdDiffs(
    x, rows=None, cols=None, na_rm=False, diff=1, trim=0, use_names=True, **_ignored
):
    """``sdDiff`` of each column."""
    return _margin(x, rows, cols, na_rm, diff, trim, use_names, 1, "sd")


def rowMadDiffs(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    diff=1,
    trim=0,
    use_names=True,
    constant=1.4826,
    low=False,
    high=False,
    center=None,
):
    """``madDiff`` of each row."""
    return _margin(
        x,
        rows,
        cols,
        na_rm,
        diff,
        trim,
        use_names,
        0,
        "mad",
        constant=constant,
        low=low,
        high=high,
        center=center,
    )


def colMadDiffs(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    diff=1,
    trim=0,
    use_names=True,
    constant=1.4826,
    low=False,
    high=False,
    center=None,
):
    """``madDiff`` of each column."""
    return _margin(
        x,
        rows,
        cols,
        na_rm,
        diff,
        trim,
        use_names,
        1,
        "mad",
        constant=constant,
        low=low,
        high=high,
        center=center,
    )


def rowIQRDiffs(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    diff=1,
    trim=0,
    use_names=True,
    type=7,
    fuzz=None,
):
    """``iqrDiff`` of each row."""
    return _margin(
        x,
        rows,
        cols,
        na_rm,
        diff,
        trim,
        use_names,
        0,
        "iqr",
        qtype=type,
        fuzz=fuzz,
    )


def colIQRDiffs(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    diff=1,
    trim=0,
    use_names=True,
    type=7,
    fuzz=None,
):
    """``iqrDiff`` of each column."""
    return _margin(
        x,
        rows,
        cols,
        na_rm,
        diff,
        trim,
        use_names,
        1,
        "iqr",
        qtype=type,
        fuzz=fuzz,
    )


def _vector(x, idxs, na_rm, diff, trim, kind, **options):
    values, is_logical = _prepare_vector(x)
    return _scale_prepared(
        values, is_logical, na_rm, diff, trim, kind, idxs=idxs, **options
    )


def _margin(x, rows, cols, na_rm, diff, trim, use_names, axis, kind, **options):
    values, is_logical = _prepare_matrix(x)
    values = _subset_matrix(values, rows, cols)
    _require_flag(use_names, "useNames")
    if values.shape[axis] == 0:
        other = values.shape[1 - axis]
        dummy = np.zeros(other, dtype=bool if is_logical else np.float64)
        _scale_prepared(dummy, is_logical, na_rm, diff, trim, kind, **options)
        return np.empty(0, dtype=np.float64)
    if axis == 0:
        rows_out = [
            _scale_prepared(values[i], is_logical, na_rm, diff, trim, kind, **options)
            for i in range(values.shape[0])
        ]
    else:
        rows_out = [
            _scale_prepared(
                values[:, j], is_logical, na_rm, diff, trim, kind, **options
            )
            for j in range(values.shape[1])
        ]
    return np.asarray(rows_out, dtype=np.float64)


def _scale_prepared(
    values,
    is_logical,
    na_rm,
    diff,
    trim,
    kind,
    idxs=None,
    constant=1.4826,
    low=False,
    high=False,
    center=None,
    qtype=7,
    fuzz=None,
):
    """One vector, in the same order as ``R/varDiff.R``."""
    diff = _check_diff(diff)
    values = np.asarray(values)
    if is_logical and values.dtype != np.float64:
        values = values.astype(np.float64)
    else:
        values = np.asarray(values, dtype=np.float64)
    if idxs is not None:
        values = _subset_values(values, idxs)
    na_rm = _require_flag(na_rm, "na.rm")
    if na_rm:
        values = values[~np.isnan(values)]
    elif kind == "iqr" and _has_missing(values):
        return float("nan")

    n = int(values.size)
    if kind in ("var", "sd") and n <= 1:
        return float("nan")
    if kind == "mad" and n <= 0:
        return float("nan")
    if kind == "iqr" and n == 0:
        return float("nan")
    if kind == "iqr" and n == 1:
        return 0.0

    if diff > 0:
        if is_logical:
            diff2(np.zeros(values.size, dtype=bool))
        values = np.asarray(diff2(values, differences=diff), dtype=np.float64)
        n = int(values.size)
        if kind in ("var", "sd", "mad") and n == 1:
            return float("nan")
        if kind == "iqr" and n == 1:
            return 0.0

    if _should_trim(trim, n):
        if kind != "iqr" and _has_missing(values):
            return float("nan")
        values = _trim_slice(values, _as_scalar_number(trim, "trim"))

    stat = _estimate(values, kind, constant, low, high, center, qtype, fuzz)
    if kind == "var":
        return float(stat / (2.0 ** diff))
    return float(stat / (math.sqrt(2.0) ** diff))


def _estimate(values, kind, constant, low, high, center, qtype, fuzz):
    if kind == "var":
        return _r_var(values)
    if kind == "sd":
        return math.sqrt(_r_var(values))
    if kind == "mad":
        return _r_mad(values, constant, low, high, center)
    return _r_iqr(values, qtype, fuzz)


def _r_var(x):
    """``stats::var`` for one numeric vector. Missing values become NA."""
    x = np.asarray(x, dtype=np.float64)
    n = int(x.size)
    if n < 2 or np.isnan(x).any():
        return float("nan")
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        wide = x.astype(np.longdouble)
        mean = wide.sum() / np.longdouble(n)
        delta = wide - mean
        sumsq = np.sum(delta * delta)
        corr = np.sum(delta)
        stat = (sumsq - (corr * corr) / np.longdouble(n)) / np.longdouble(n - 1)
    if not np.isfinite(stat):
        return float("nan")
    return float(stat)


def _median(x):
    """``stats::median``. An even count is the mean of the two central values."""
    x = np.asarray(x, dtype=np.float64)
    n = int(x.size)
    if n == 0 or np.isnan(x).any():
        return float("nan")
    ordered = np.sort(x)
    half = (n + 1) // 2
    if n % 2 == 1:
        return float(ordered[half - 1])
    left = np.longdouble(ordered[half - 1])
    right = np.longdouble(ordered[half])
    return float((left + right) / np.longdouble(2))


def _r_mad(x, constant, low, high, center):
    """``stats::mad`` with ``na.rm = FALSE``."""
    x = np.asarray(x, dtype=np.float64)
    constant = _as_scalar_number(constant, "constant")
    low = _require_flag(low, "low")
    high = _require_flag(high, "high")
    n = int(x.size)
    if center is None:
        center = _median(x)
    else:
        center = _as_scalar_number(center, "center")
    with np.errstate(invalid="ignore"):
        dev = np.abs(x - center)
    if (low or high) and n % 2 == 0:
        if low and high:
            raise ValueError("'low' and 'high' cannot be both TRUE")
        if n == 0 or np.isnan(dev).any():
            return float("nan")
        ordered = np.sort(dev)
        n2 = n // 2 + (1 if high else 0)
        return float(constant) * float(ordered[n2 - 1])
    return float(constant) * _median(dev)


def _r_iqr(x, qtype, fuzz):
    """Difference of the 0.25 and 0.75 quantiles."""
    x = np.asarray(x, dtype=np.float64)
    if x.size and np.isnan(x).any():
        raise ValueError("missing values and NaN's not allowed if 'na.rm' is FALSE")
    type_ = _check_type(qtype)
    if fuzz is None:
        fuzz = 0.0 if type_ == 7 else 4.0 * float(np.finfo(np.float64).eps)
    else:
        fuzz = _as_scalar_number(fuzz, "fuzz")
        if not math.isfinite(fuzz) or fuzz < 0:
            raise ValueError("fuzz must be a single non-negative finite number")
    quartiles = _quantile(x, np.array([0.25, 0.75]), type_, fuzz)
    return float(quartiles[1] - quartiles[0])


def _quantile(x, probs, type_, fuzz):
    """``stats::quantile`` for finite probabilities. Empty input is NA."""
    x = np.asarray(x, dtype=np.float64)
    probs = np.asarray(probs, dtype=np.float64)
    n = int(x.size)
    if n == 0:
        return np.full(probs.shape, np.nan)
    ordered = np.sort(x)
    if type_ == 7:
        index = 1.0 + max(n - 1, 0) * probs
        lo = np.floor(index * (1.0 + fuzz))
        hi = np.ceil(index)
        lo_i = lo.astype(np.int64)
        hi_i = hi.astype(np.int64)
        qs = ordered[lo_i - 1].astype(np.float64, copy=True)
        upper = ordered[hi_i - 1]
        move = (index > lo) & (upper != qs)
        if np.any(move):
            h = (index - lo)[move]
            qs[move] = (1.0 - h) * qs[move] + h * upper[move]
        return qs
    if type_ <= 3:
        nppm = n * probs - 0.5 if type_ == 3 else n * probs
        j = _floor_fuzz(nppm, fuzz)
        if type_ == 1:
            h = (nppm > j).astype(np.float64)
        elif type_ == 2:
            h = ((nppm > j).astype(np.float64) + 1.0) / 2.0
        else:
            h = ((nppm != j) | ((j.astype(np.int64) % 2) == 1)).astype(np.float64)
        return _order_quantile(ordered, j, h)
    a, b = {
        4: (0.0, 1.0),
        5: (0.5, 0.5),
        6: (0.0, 0.0),
        8: (1.0 / 3.0, 1.0 / 3.0),
        9: (3.0 / 8.0, 3.0 / 8.0),
    }[type_]
    nppm = a + probs * (n + 1.0 - a - b)
    j = _floor_fuzz(nppm, fuzz)
    h = nppm - j
    h = np.array(h, dtype=np.float64, copy=True)
    h[np.abs(h) < fuzz] = 0.0
    return _order_quantile(ordered, j, h)


def _order_quantile(ordered, j, h):
    """Types 1-6, 8 and 9, after R pads the sample with its endpoints."""
    first = float(ordered[0])
    last = float(ordered[-1])
    padded = np.concatenate(
        [np.array([first, first]), ordered, np.array([last, last])]
    )
    j = np.asarray(j, dtype=np.int64)
    h = np.asarray(h, dtype=np.float64)
    lower = padded[j + 1]
    upper = padded[j + 2]
    qs = np.array(lower, dtype=np.float64, copy=True)
    take_upper = h == 1.0
    qs[take_upper] = upper[take_upper]
    other = (h > 0.0) & (h < 1.0) & (lower != upper)
    if np.any(other):
        weight = h[other]
        qs[other] = (1.0 - weight) * lower[other] + weight * upper[other]
    return qs


def _floor_fuzz(values, fuzz):
    return np.floor(np.asarray(values, dtype=np.float64) * (1.0 + fuzz))


def _check_type(type_):
    arr = np.asarray(type_)
    if getattr(arr.dtype, "kind", "") not in "iuf" or arr.size != 1:
        raise ValueError("'type' must be an integer in 1..9")
    value = float(arr.reshape(-1)[0])
    if not math.isfinite(value) or value != math.trunc(value) or int(value) not in range(1, 10):
        raise ValueError("'type' must be an integer in 1..9")
    return int(value)


def _check_diff(diff):
    """Length and sign checks, then the original numeric value."""
    if isinstance(diff, (bool, np.bool_)):
        return float(bool(diff))
    if diff is None:
        raise ValueError("Argument 'diff' is not scalar: 0")
    arr = np.asarray(diff)
    if getattr(arr.dtype, "kind", "") not in "iuf":
        raise ValueError("Argument 'diff' must be numeric")
    flat = np.ravel(arr, order="F")
    if flat.size != 1:
        raise ValueError(f"Argument 'diff' is not scalar: {flat.size}")
    value = float(flat[0])
    if math.isnan(value):
        raise ValueError("missing value where TRUE/FALSE needed")
    if value < 0:
        if not value.is_integer():
            raise ValueError(
                "invalid format '%d'; use format %f, %e, %g or %a for numeric objects"
            )
        raise ValueError(f"Argument 'diff' must not be negative: {int(value)}")
    return value


def _should_trim(trim, n):
    """``trim > 0 && n > 0``. A missing trim is an error only when ``n > 0``."""
    number = _as_scalar_number(trim, "trim")
    if math.isnan(number):
        if n > 0:
            raise ValueError("missing value where TRUE/FALSE needed")
        return False
    return number > 0 and n > 0


def _trim_slice(values, trim):
    """``sort`` then the 1-based inclusive slice ``lo:hi`` from ``R/varDiff.R``."""
    n = int(values.size)
    lo = math.floor(n * trim) + 1
    hi = (n + 1) - lo
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    if lo <= hi:
        indexes = range(lo, hi + 1)
    else:
        indexes = range(lo, hi - 1, -1)
    picked = []
    for index in indexes:
        if index == 0:
            continue
        if index < 1 or index > n:
            picked.append(np.nan)
        else:
            picked.append(ordered[index - 1])
    if not picked:
        return np.empty(0, dtype=np.float64)
    return np.asarray(picked, dtype=np.float64)


def _has_missing(values):
    if values.size == 0:
        return False
    return bool(anyMissing(np.ascontiguousarray(values, dtype=np.float64)))


def _prepare_vector(x):
    """Return float values and whether ``x`` is logical.

    A matrix is read in column-major order, matching R's underlying vector.
    Integer ``NA`` becomes NaN before ``diff2``, which works in float64.
    """
    if isinstance(x, (bool, np.bool_)):
        return np.array([1.0 if bool(x) else 0.0]), True
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        number = np.nan if int(x) == NA_INTEGER else float(x)
        return np.array([number], dtype=np.float64), False
    if isinstance(x, (float, np.floating)):
        return np.array([float(x)], dtype=np.float64), False
    if isinstance(x, (list, tuple)):
        return _from_sequence(x)
    arr = np.asarray(x)
    if arr.dtype == object:
        return _from_sequence(np.ravel(arr, order="F").tolist())
    if arr.ndim == 0:
        arr = arr.reshape(1)
    else:
        arr = np.ravel(arr, order="F")
    return _array_values(arr)


def _prepare_matrix(x):
    arr = np.asarray(x) if not isinstance(x, (list, tuple)) else np.array(x, dtype=object)
    if isinstance(x, (list, tuple)) and arr.dtype != object:
        arr = np.asarray(x)
    if getattr(arr.dtype, "kind", "") == "O" or (
        isinstance(x, (list, tuple)) and _sequence_is_object_matrix(x)
    ):
        return _matrix_from_object(x)
    if arr.ndim != 2:
        raise ValueError("incorrect number of dimensions")
    values, is_logical = _array_values(arr)
    return values.reshape(arr.shape), is_logical


def _sequence_is_object_matrix(x):
    return any(isinstance(row, (list, tuple, np.ndarray)) for row in x)


def _matrix_from_object(x):
    rows = []
    logical = True
    for row in x:
        if isinstance(row, (list, tuple)):
            values, row_logical = _from_sequence(list(row))
        else:
            values, row_logical = _prepare_vector(row)
        rows.append(values)
        logical = logical and row_logical
    width = {int(row.size) for row in rows}
    if len(width) != 1:
        raise ValueError("incorrect number of dimensions")
    return np.vstack(rows), logical


def _from_sequence(seq):
    if len(seq) == 0:
        return np.empty(0, dtype=np.float64), False
    if all(item is None or isinstance(item, (bool, np.bool_)) for item in seq):
        out = np.empty(len(seq), dtype=np.float64)
        for i, item in enumerate(seq):
            if item is None:
                out[i] = np.nan
            else:
                out[i] = 1.0 if bool(item) else 0.0
        return out, True
    out = np.empty(len(seq), dtype=np.float64)
    for i, item in enumerate(seq):
        if item is None:
            out[i] = np.nan
        elif isinstance(item, (bool, np.bool_)):
            out[i] = 1.0 if bool(item) else 0.0
        elif isinstance(item, (int, np.integer)):
            out[i] = np.nan if int(item) == NA_INTEGER else float(item)
        elif isinstance(item, (float, np.floating)):
            out[i] = float(item)
        else:
            raise ValueError("Argument 'x' must be numeric")
    return out, False


def _array_values(arr):
    if arr.dtype == np.bool_:
        return arr.astype(np.float64), True
    if np.issubdtype(arr.dtype, np.integer):
        out = arr.astype(np.float64)
        out[arr.astype(np.int64) == NA_INTEGER] = np.nan
        return out, False
    if np.issubdtype(arr.dtype, np.floating):
        return np.asarray(arr, dtype=np.float64), False
    raise ValueError("Argument 'x' must be numeric")


def _subset_matrix(values, rows, cols):
    if rows is not None:
        values = _take(values, _positions(rows, values.shape[0]), axis=0)
    if cols is not None:
        values = _take(values, _positions(cols, values.shape[1]), axis=1)
    return values


def _subset_values(values, idxs):
    positions = _positions(idxs, int(values.size))
    out = np.empty(positions.size, dtype=np.float64)
    if positions.size == 0:
        return out
    missing = positions < 0
    out[missing] = np.nan
    keep = ~missing
    out[keep] = values[positions[keep]]
    return out


def _take(values, positions, axis):
    if positions.size == 0:
        shape = list(values.shape)
        shape[axis] = 0
        return np.empty(shape, dtype=np.float64)
    missing = positions < 0
    if axis == 0:
        out = np.empty((positions.size, values.shape[1]), dtype=np.float64)
        if np.any(~missing):
            out[~missing] = values[positions[~missing]]
        out[missing] = np.nan
        return out
    out = np.empty((values.shape[0], positions.size), dtype=np.float64)
    if np.any(~missing):
        out[:, ~missing] = values[:, positions[~missing]]
    out[:, missing] = np.nan
    return out


def _positions(index, n):
    """1-based base-R ``[`` positions. ``-1`` means a missing selection."""
    if isinstance(index, (bool, np.bool_)):
        return _logical_positions([bool(index)], n)
    if isinstance(index, (list, tuple)):
        if len(index) == 0:
            return np.empty(0, dtype=np.int64)
        if all(item is None or isinstance(item, (bool, np.bool_)) for item in index):
            return _logical_positions(list(index), n)
    arr = np.asarray(index)
    if arr.dtype == object:
        items = np.ravel(arr, order="F").tolist()
        if all(item is None or isinstance(item, (bool, np.bool_)) for item in items):
            return _logical_positions(items, n)
        return _numeric_positions(np.array(_object_numbers(items), dtype=np.float64), n)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    else:
        arr = np.ravel(arr, order="F")
    if arr.size == 0:
        return np.empty(0, dtype=np.int64)
    if arr.dtype == np.bool_:
        return _logical_positions(arr.tolist(), n)
    if getattr(arr.dtype, "kind", "") not in "iuf":
        raise ValueError("idxs can only be integer, numeric, or logical")
    return _numeric_positions(arr, n)


def _object_numbers(items):
    numbers = []
    for item in items:
        if item is None:
            numbers.append(np.nan)
        elif isinstance(item, (bool, np.bool_)):
            raise ValueError("only 0's may be mixed with negative subscripts")
        elif isinstance(item, (int, np.integer)):
            numbers.append(np.nan if int(item) == NA_INTEGER else float(item))
        elif isinstance(item, (float, np.floating)):
            numbers.append(float(item))
        else:
            raise ValueError("idxs can only be integer, numeric, or logical")
    return numbers


def _logical_positions(mask, n):
    length = len(mask)
    if length == 0:
        return np.empty(0, dtype=np.int64)
    positions = []
    if length > n:
        for i, flag in enumerate(mask):
            if flag is None:
                positions.append(-1)
            elif flag and i < n:
                positions.append(i)
            elif flag:
                positions.append(-1)
        return np.asarray(positions, dtype=np.int64)
    for i in range(n):
        flag = mask[i % length]
        if flag is None:
            positions.append(-1)
        elif flag:
            positions.append(i)
    return np.asarray(positions, dtype=np.int64)


def _numeric_positions(arr, n):
    if np.issubdtype(arr.dtype, np.integer):
        as_int = arr.astype(np.int64)
        raw = as_int.astype(np.float64)
        raw[as_int == NA_INTEGER] = np.nan
    else:
        raw = arr.astype(np.float64)
    truncated = np.trunc(raw)
    finite = truncated[np.isfinite(truncated)]
    has_negative = bool(np.any(finite < 0))
    has_positive = bool(np.any(finite > 0))
    has_missing = bool(np.any(~np.isfinite(truncated)))
    if has_negative and (has_positive or has_missing):
        raise ValueError("only 0's may be mixed with negative subscripts")
    if has_negative:
        drop = set()
        for value in finite:
            magnitude = -int(value)
            if 1 <= magnitude <= n:
                drop.add(magnitude)
        keep = [i - 1 for i in range(1, n + 1) if i not in drop]
        return np.asarray(keep, dtype=np.int64)
    positions = []
    for value in truncated:
        if not np.isfinite(value) or value == 0:
            if not np.isfinite(value):
                positions.append(-1)
            continue
        index = int(value)
        positions.append(index - 1 if 1 <= index <= n else -1)
    return np.asarray(positions, dtype=np.int64)


def _as_scalar_number(value, name):
    if isinstance(value, (bool, np.bool_)):
        return float(bool(value))
    arr = np.asarray(value)
    if getattr(arr.dtype, "kind", "") not in "iuf":
        raise ValueError(f"Argument '{name}' must be numeric")
    flat = np.ravel(arr, order="F")
    if flat.size != 1:
        raise ValueError(f"Argument '{name}' is not a scalar: {flat.size}")
    return float(flat[0])


def _require_flag(value, name):
    if value is None or (
        isinstance(value, (float, np.floating)) and math.isnan(float(value))
    ):
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(value, np.ndarray) and value.dtype.kind == "f" and np.isnan(value).any():
        raise ValueError("missing value where TRUE/FALSE needed")
    return as_logical(value, name)
