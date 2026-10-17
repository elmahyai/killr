"""Row and column quantiles, ported from matrixStats.

``rows`` and ``cols`` are 1-based. ``None`` selects every row or column.
A double missing value is ``nan``. An integer missing value is R's
integer NA, the minimum int32. Quantiles follow the installed
``stats::quantile`` (R 4.5), including types 1 through 9. The type-7
path with no missing values follows matrixStats and does not clamp
probabilities before the partial-sort indexes are formed.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = ["rowQuantiles", "colQuantiles"]

_EPS = float(np.finfo(np.float64).eps)
_DEFAULT_FUZZ = 4.0 * _EPS
_PROB_EPS = 100.0 * _EPS
_NA_INTEGER = np.int32(np.iinfo(np.int32).min)
_DEFAULT_PROBS = np.array([0.0, 0.25, 0.5, 0.75, 1.0], dtype=np.float64)


class _Result(np.ndarray):
    """Numeric result with the percentage names matrixStats attaches."""

    def __new__(cls, data, names=None, rownames=None, colnames=None):
        obj = np.array(data, copy=True).view(cls)
        obj.names = None if names is None else tuple(names)
        obj.rownames = None if rownames is None else tuple(rownames)
        obj.colnames = None if colnames is None else tuple(colnames)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.names = getattr(obj, "names", None)
        self.rownames = getattr(obj, "rownames", None)
        self.colnames = getattr(obj, "colnames", None)


def rowQuantiles(
    x,
    rows=None,
    cols=None,
    probs=None,
    na_rm=False,
    type=7,
    digits=7,
    use_names=True,
    drop=True,
    fuzz=None,
):
    """Quantiles of each row.

    Mirrors ``matrixStats::rowQuantiles``. ``probs`` defaults to
    ``0, 0.25, 0.5, 0.75, 1``. ``type`` is the ``stats::quantile``
    estimator, 7 by default. ``digits`` sets the percentage column
    names, such as ``"25%"`` and ``"75%"``. ``use_names`` is
    ``useNames``. ``drop`` drops dimensions of length 1, as R's
    ``drop`` does.
    """
    return _quantiles(
        x, rows, cols, probs, na_rm, type, digits, use_names, drop, fuzz, by_row=True
    )


def colQuantiles(
    x,
    rows=None,
    cols=None,
    probs=None,
    na_rm=False,
    type=7,
    digits=7,
    use_names=True,
    drop=True,
    fuzz=None,
):
    """Quantiles of each column.

    Mirrors ``matrixStats::colQuantiles``. Arguments match
    :func:`rowQuantiles`. The result has one row per selected column.
    """
    return _quantiles(
        x, rows, cols, probs, na_rm, type, digits, use_names, drop, fuzz, by_row=False
    )


def _quantiles(
    x, rows, cols, probs, na_rm, type, digits, use_names, drop, fuzz, by_row
):
    kind, matrix = _as_matrix(x)
    probabilities = _as_probs(probs)
    use_names = _as_flag(use_names, "useNames")
    drop = _as_flag(drop, "drop")
    type_missing = _is_missing_number(type)
    if type_missing:
        raise ValueError("missing value where TRUE/FALSE needed")
    type_number = _type_number(type)
    type_is_seven = type_number == 7

    row_pos = resolve_index(rows, matrix.shape[0], "rows")
    col_pos = resolve_index(cols, matrix.shape[1], "cols")
    values = _gather(_to_float(matrix, kind), row_pos, col_pos)

    nrow, ncol = values.shape
    nprob = int(probabilities.size)
    out_rows = nrow if by_row else ncol
    if nrow == 0 or ncol == 0 or nprob == 0:
        result = _empty_values(kind, type_is_seven, (out_rows, nprob))
    else:
        choice = _require_type(type_number)
        block = values if by_row else values.T
        result = _margin_quantiles(block, probabilities, choice, na_rm, fuzz)

    if use_names and nprob > 0:
        colnames = _prob_names(probabilities, digits)
    else:
        colnames = None
    return _maybe_drop(result, colnames, drop, use_names)


def _margin_quantiles(values, probs, type_number, na_rm, fuzz):
    """Quantiles of each row of ``values``. Missing entries are ``nan``."""
    miss = np.isnan(values)
    has = miss.any(axis=1)
    any_missing = bool(has.any())
    # No missing values makes na.rm irrelevant, as in the R function.
    if not any_missing:
        na_rm_flag = False
    else:
        na_rm_flag = _as_flag(na_rm, "na.rm")

    if not any_missing and type_number == 7:
        order = np.sort(values, axis=1)
        return _type7_partial(order, probs)

    out = np.full((values.shape[0], probs.size), np.nan, dtype=np.float64)
    clean = ~has
    if type_number == 7 and np.any(clean):
        order = np.sort(values[clean], axis=1)
        out[clean] = _type7_quantile(order, probs, fuzz)
        pending = np.flatnonzero(has) if na_rm_flag else ()
    elif na_rm_flag:
        pending = np.arange(values.shape[0])
    else:
        pending = np.flatnonzero(clean)
    for index in pending:
        row = values[index]
        if na_rm_flag:
            row = row[~np.isnan(row)]
        elif np.isnan(row).any():
            continue
        out[index] = _r_quantile(row, probs, type_number, fuzz)
    return out


def _type7_partial(order, probs):
    """matrixStats type-7 path: no probability clamp, then partial indexes."""
    n = order.shape[1]
    index = 1.0 + (n - 1.0) * probs
    lo = np.floor(index)
    hi = np.ceil(index)
    if np.any(lo < 1.0) or np.any(hi > n) or np.any(lo > n) or np.any(hi < 1.0):
        bad = _first_bad_index(lo, hi, n)
        raise ValueError(f"'partial' index {bad} outside bounds")
    return _blend(order, index, lo, hi)


def _type7_quantile(order, probs, fuzz):
    """``stats::quantile`` type 7, which clamps probabilities into [0, 1]."""
    fuzz_value = 0.0 if fuzz is None else _as_fuzz(fuzz)
    p = np.clip(probs, 0.0, 1.0)
    n = order.shape[1]
    index = 1.0 + max(n - 1, 0) * p
    lo = np.floor(index * (1.0 + fuzz_value))
    hi = np.ceil(index)
    return _blend(order, index, lo, hi)


def _blend(order, index, lo, hi):
    lo_i = lo.astype(np.intp) - 1
    hi_i = hi.astype(np.intp) - 1
    left = order[:, lo_i]
    right = order[:, hi_i]
    weight = index - lo
    return (1.0 - weight) * left + weight * right


def _first_bad_index(lo, hi, n):
    for value in np.concatenate([lo, hi]):
        if value < 1.0 or value > n:
            return int(value)
    return int(lo[0])


def _r_quantile(x, probs, type_number, fuzz):
    """One vector, matching ``stats::quantile`` in R 4.5. ``x`` has no NA."""
    fuzz_value = (
        (0.0 if type_number == 7 else _DEFAULT_FUZZ) if fuzz is None else _as_fuzz(fuzz)
    )
    p = np.clip(np.asarray(probs, dtype=np.float64), 0.0, 1.0)
    n = int(x.size)
    if n == 0 or p.size == 0:
        return np.full(p.size, np.nan, dtype=np.float64)
    xs = np.sort(np.asarray(x, dtype=np.float64))

    def floor_f(arr):
        return np.floor(np.asarray(arr, dtype=np.float64) * (1.0 + fuzz_value))

    if type_number == 7:
        index = 1.0 + max(n - 1, 0) * p
        lo = floor_f(index)
        hi = np.ceil(index)
        qs = xs[lo.astype(np.intp) - 1].astype(np.float64, copy=True)
        hi_i = hi.astype(np.intp) - 1
        take = (index > lo) & (xs[hi_i] != qs)
        if np.any(take):
            weight = (index - lo)[take]
            qs[take] = (1.0 - weight) * qs[take] + weight * xs[hi_i[take]]
        return qs

    if type_number <= 3:
        nppm = n * p - 0.5 if type_number == 3 else n * p
        j = floor_f(nppm)
        if type_number == 1:
            h = (nppm > j).astype(np.float64)
        elif type_number == 2:
            h = ((nppm > j).astype(np.float64) + 1.0) / 2.0
        else:
            h = np.logical_or(nppm != j, (j.astype(np.intp) % 2) == 1).astype(np.float64)
    else:
        a, b = _continuous_ab(type_number)
        nppm = a + p * (n + 1.0 - a - b)
        j = floor_f(nppm)
        h = nppm - j
        h = np.array(h, dtype=np.float64, copy=True)
        h[np.abs(h) < fuzz_value] = 0.0

    padded = np.empty(n + 4, dtype=np.float64)
    padded[0] = xs[0]
    padded[1] = xs[0]
    padded[2 : n + 2] = xs
    padded[n + 2] = xs[-1]
    padded[n + 3] = xs[-1]
    j_i = j.astype(np.intp)
    lower = padded[j_i + 1]
    upper = padded[j_i + 2]
    qs = lower.astype(np.float64, copy=True)
    at_one = h == 1.0
    qs[at_one] = upper[at_one]
    other = (h > 0.0) & (h < 1.0) & (lower != upper)
    if np.any(other):
        qs[other] = ((1.0 - h) * lower + h * upper)[other]
    return qs


def _continuous_ab(type_number):
    if type_number == 4:
        return 0.0, 1.0
    if type_number == 5:
        return 0.5, 0.5
    if type_number == 6:
        return 0.0, 0.0
    if type_number == 8:
        return 1.0 / 3.0, 1.0 / 3.0
    if type_number == 9:
        return 3.0 / 8.0, 3.0 / 8.0
    raise ValueError("'type' must be an integer in 1..9")


def _empty_values(kind, type_is_seven, shape):
    if type_is_seven or kind != "integer":
        return np.full(shape, np.nan, dtype=np.float64)
    return np.full(shape, _NA_INTEGER, dtype=np.int32)


def _maybe_drop(values, colnames, drop, use_names):
    rownames = None
    if not drop:
        return _Result(
            values,
            rownames=rownames if use_names else None,
            colnames=colnames if use_names else None,
        )
    nrow, ncol = values.shape
    if nrow == 1 and ncol == 1:
        return _Result(values.reshape(1))
    if nrow == 1:
        return _Result(values.reshape(ncol), names=colnames if use_names else None)
    if ncol == 1:
        return _Result(values.reshape(nrow), names=rownames if use_names else None)
    return _Result(values, colnames=colnames if use_names else None)


def _as_matrix(x):
    if isinstance(x, (bool, np.bool_)):
        _defunct("logical")
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        _defunct("integer")
    if isinstance(x, (float, np.floating)):
        _defunct("numeric")
    if isinstance(x, str):
        _defunct("character")
    array = np.asarray(x)
    if array.ndim != 2:
        _defunct(_class_name(array))
    if array.dtype == np.bool_:
        return "logical", array
    if np.issubdtype(array.dtype, np.integer):
        return "integer", _as_int32(array)
    if np.issubdtype(array.dtype, np.floating):
        return "double", np.asarray(array, dtype=np.float64)
    if array.dtype.kind in "SU":
        raise ValueError(
            "Argument 'x' is of type 'character'. Only 'integer', 'numeric', and 'logical' is supported."
        )
    if np.issubdtype(array.dtype, np.complexfloating):
        raise ValueError(
            "Argument 'x' is of type 'complex'. Only 'integer', 'numeric', and 'logical' is supported."
        )
    raise ValueError(
        "Argument 'x' is of type "
        f"'{array.dtype.name}'. Only 'integer', 'numeric', and 'logical' is supported."
    )


def _defunct(kind):
    raise ValueError(
        f"[matrixStats] Argument 'x' is of class '{kind}', but should be a matrix. "
        f"The use of a '{kind}' is not supported, the correctness of the result is not "
        "guaranteed. Please update your code accordingly."
    )


def _class_name(array):
    if array.dtype == np.bool_ or array.dtype.kind == "b":
        return "logical"
    if np.issubdtype(array.dtype, np.integer):
        return "integer"
    if np.issubdtype(array.dtype, np.floating):
        return "numeric"
    if array.dtype.kind in "SU":
        return "character"
    return array.dtype.name


def _as_int32(array):
    if array.dtype == np.int32:
        return array
    wide = np.asarray(array, dtype=np.int64)
    if wide.size and (np.any(wide < int(_NA_INTEGER)) or np.any(wide > np.iinfo(np.int32).max)):
        raise ValueError("Argument 'x' integer values do not fit in a 32-bit integer")
    return wide.astype(np.int32)


def _to_float(matrix, kind):
    if kind == "logical":
        return matrix.astype(np.float64)
    if kind == "integer":
        out = matrix.astype(np.float64)
        out[matrix == _NA_INTEGER] = np.nan
        return out
    return np.asarray(matrix, dtype=np.float64)


def _gather(data, row_pos, col_pos):
    if all(pos is not None for pos in row_pos) and all(pos is not None for pos in col_pos):
        rows = np.asarray(row_pos, dtype=np.intp)
        cols = np.asarray(col_pos, dtype=np.intp)
        return data[np.ix_(rows, cols)]
    out = np.empty((len(row_pos), len(col_pos)), dtype=np.float64)
    for i, row in enumerate(row_pos):
        if row is None:
            out[i] = np.nan
            continue
        for j, col in enumerate(col_pos):
            out[i, j] = np.nan if col is None else data[row, col]
    return out


def _as_probs(probs):
    if probs is None:
        return _DEFAULT_PROBS.copy()
    try:
        array = np.asarray(probs, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("Argument 'probs' must be numeric") from exc
    if array.ndim == 0:
        array = array.reshape(1)
    array = np.ravel(array)
    if np.any(np.isnan(array)):
        raise ValueError("Argument 'probs' must not contain missing values")
    outside = (array < -_PROB_EPS) | (array > 1.0 + _PROB_EPS)
    if np.any(outside):
        bad = float(array[outside][0])
        raise ValueError(
            f"Argument 'probs' is out of range [0-eps, 1+eps]: {bad:.6g}"
        )
    return np.ascontiguousarray(array)


def _is_missing_number(value):
    if value is None:
        return True
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return True
    array = np.asarray(value)
    if array.size == 1 and np.issubdtype(array.dtype, np.floating):
        return bool(np.isnan(array.reshape(-1)[0]))
    return False


def _type_number(type_):
    array = np.asarray(type_)
    if array.size != 1 or not (
        np.issubdtype(array.dtype, np.number) or array.dtype == np.bool_
    ):
        raise ValueError("'type' must be an integer in 1..9")
    if array.dtype == np.bool_:
        raise ValueError("'type' must be an integer in 1..9")
    return float(array.reshape(-1)[0])


def _require_type(number):
    for choice in range(1, 10):
        if number == choice:
            return choice
    raise ValueError("'type' must be an integer in 1..9")


def _as_fuzz(fuzz):
    array = np.asarray(fuzz)
    if array.size != 1 or not np.issubdtype(array.dtype, np.number):
        raise ValueError("fuzz must be one non-negative finite number")
    value = float(array.reshape(-1)[0])
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("fuzz must be one non-negative finite number")
    return value


def _as_flag(value, name):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool) and int(value) in (0, 1):
        return bool(int(value))
    raise ValueError(f"Argument '{name}' must be either TRUE or FALSE")


def _prob_names(probs, digits):
    number = _digits_number(digits)
    scaled = 100.0 * np.asarray(probs, dtype=np.float64)
    places = int(math.trunc(number))
    if scaled.size < 100:
        return tuple(_format_fg(float(value), places) + "%" for value in scaled)
    return tuple(text + "%" for text in _format_vector(scaled, places))


def _digits_number(digits):
    array = np.asarray(digits)
    if array.size != 1 or array.dtype == np.bool_ or not np.issubdtype(array.dtype, np.number):
        raise ValueError("Argument 'digits' is not a single positive numeric")
    value = float(array.reshape(-1)[0])
    if not math.isfinite(value) or value < 1.0:
        raise ValueError("Argument 'digits' is not a single positive numeric")
    return value


def _frexp10(ax):
    exp = math.floor(math.log10(ax))
    power = 10.0 ** exp
    if ax < power:
        exp -= 1
    elif ax >= power * 10.0:
        exp += 1
    return exp


def _round_places(value, places):
    if places >= 0:
        return round(value, places)
    factor = 10.0 ** (-places)
    return round(value / factor) * factor


def _format_fg(x, digits):
    """R ``formatC(..., format='fg', width=1)`` for one finite number."""
    if x == 0.0:
        return "0"
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    sign = "-" if x < 0.0 else ""
    ax = abs(float(x))
    exp = _frexp10(ax)
    dec = digits - exp - 1
    if dec >= 0:
        rounded = _round_places(ax, dec)
        rexp = _frexp10(rounded) if rounded > 0.0 else exp
        if digits == 1 and ax < 10.0 and rounded >= 10.0:
            return sign + "1e+01"
        if rexp != exp and dec > 0:
            dec2 = digits - rexp - 1
            if dec2 < 0:
                text = str(int(round(rounded)))
            else:
                text = f"{rounded:.{dec2}f}"
                if "." in text:
                    text = text.rstrip("0").rstrip(".")
            return sign + text
        if dec == 0:
            return sign + str(int(round(rounded)))
        text = f"{rounded:.{dec}f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return sign + text
    factor = 10.0 ** (exp - digits + 1)
    sig = round(ax / factor) * factor
    # formatC drops the sign when this rounding carries to the next power of ten.
    if sig > 0.0 and _frexp10(sig) > exp:
        return str(int(round(sig)))
    return sign + str(int(round(_round_places(ax, 0))))


def _format_vector(values, digits):
    """R ``format(trim=TRUE)`` for a percentage vector of length at least 100."""
    vals = [float(value) for value in values]
    finite = [abs(value) for value in vals if math.isfinite(value) and value != 0.0]
    if not finite:
        return ["0" if value == 0.0 else _format_fg(value, digits) for value in vals]
    emin = _frexp10(min(finite))
    dec = max(0, digits - emin - 1)
    texts = []
    for value in vals:
        if dec == 0:
            texts.append(str(int(round(value))))
        else:
            texts.append(f"{value:.{dec}f}")
    return texts


def resolve_index(index, n, what):
    """1-based R subscript. ``None`` means every position.

    The result is a list of 0-based positions. ``None`` in that list is an
    NA subscript, which inserts a missing row or column.
    """
    if index is None:
        return list(range(n))
    kind, values = _coerce_index(index, what)
    if kind == "logical":
        return _logical_index(values, n)
    return _numeric_index(values, n)


def _coerce_index(index, what):
    if isinstance(index, str):
        raise ValueError("no 'dimnames' attribute for array")
    if isinstance(index, (bool, np.bool_)):
        return "logical", [bool(index)]
    if isinstance(index, (int, np.integer)) and not isinstance(index, bool):
        return "numeric", [int(index)]
    if isinstance(index, (float, np.floating)):
        return "numeric", [_trunc_index(float(index))]

    if isinstance(index, (list, tuple)):
        if index and all(isinstance(value, str) for value in index):
            raise ValueError("no 'dimnames' attribute for array")
        if all(_is_logical_entry(value) for value in index):
            logical = []
            for value in index:
                logical.append(None if value is None else bool(value))
            return "logical", logical
        numeric = []
        for value in index:
            numeric.append(_one_numeric(value, what))
        return "numeric", numeric

    array = np.asarray(index)
    if array.dtype.kind in "SU":
        raise ValueError("no 'dimnames' attribute for array")
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        raise ValueError(f"Argument '{what}' must be a vector")
    if array.dtype == np.bool_:
        return "logical", [bool(value) for value in array]
    if array.dtype == object:
        if any(isinstance(value, str) for value in array):
            raise ValueError("no 'dimnames' attribute for array")
        if all(_is_logical_entry(value) for value in array):
            logical = []
            for value in array:
                logical.append(None if value is None else bool(value))
            return "logical", logical
        return "numeric", [_one_numeric(value, what) for value in array]
    if np.issubdtype(array.dtype, np.integer):
        return "numeric", [int(value) for value in array]
    if np.issubdtype(array.dtype, np.floating):
        return "numeric", [_trunc_index(float(value)) for value in array]
    raise ValueError(f"Argument '{what}' must be numeric or logical")


def _is_logical_entry(value):
    return value is None or isinstance(value, (bool, np.bool_))


def _one_numeric(value, what):
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return 1 if value else 0
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return _trunc_index(float(value))
    raise ValueError(f"Argument '{what}' must be numeric or logical")


def _trunc_index(value):
    if not math.isfinite(value):
        return None
    return int(math.trunc(value))


def _logical_index(flags, n):
    if not flags:
        return []
    if len(flags) > n:
        for flag in flags[n:]:
            if flag is not False:
                raise ValueError("subscript out of bounds")
        flags = flags[:n]
    chosen = []
    length = len(flags)
    for position in range(n):
        flag = flags[position % length]
        if flag is None:
            chosen.append(None)
        elif flag:
            chosen.append(position)
    return chosen


def _numeric_index(values, n):
    if any(value is not None and value < 0 for value in values):
        if any(value is not None and value > 0 for value in values):
            raise ValueError("only 0's may be mixed with negative subscripts")
        excluded = set()
        for value in values:
            if value is None:
                raise ValueError("missing values are not allowed in negative subscripts")
            if value == 0:
                continue
            position = -value
            if position > n:
                raise ValueError("subscript out of bounds")
            excluded.add(position)
        return [position for position in range(n) if (position + 1) not in excluded]
    chosen = []
    for value in values:
        if value is None:
            chosen.append(None)
            continue
        if value == 0:
            continue
        if value > n:
            raise ValueError("subscript out of bounds")
        chosen.append(value - 1)
    return chosen


def quantile_vector(x, probs, type=7, fuzz=None):
    """``stats::quantile`` for one numeric vector with no missing values.

    Used by :func:`matrixstats.iqr.iqr`. ``probs`` are not rechecked.
    """
    number = _type_number(type)
    choice = _require_type(number)
    return _r_quantile(np.asarray(x, dtype=np.float64), np.asarray(probs, dtype=np.float64), choice, fuzz)
