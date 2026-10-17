"""`near()` from dplyr 1.2.1.

`abs(x - y) < tol`, with R's arithmetic: integer subtraction overflows to NA,
`NULL` has length zero, and a longer vector that is not a multiple warns and
still recycles. The default tolerance is `.Machine$double.eps^0.5`.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from dplyr._vec import Factor, Logical, Vec, _INT_MAX, _INT_MIN

_MISSING = object()
_SQRT_EPS = float(np.sqrt(np.float64(np.finfo(np.float64).eps)))


class _Num:
    def __init__(self, kind, values, names=None, shape=None):
        self.kind = kind
        self.values = values
        self.names = names
        self.shape = shape

    def __len__(self):
        return len(self.values)


def _clean_float(value):
    if value is None:
        return None
    number = float(value)
    if math.isnan(number):
        return None
    return number


def _as_double_list(values):
    out = []
    for value in values:
        if value is None:
            out.append(None)
        elif isinstance(value, bool):
            out.append(1.0 if value else 0.0)
        else:
            out.append(_clean_float(value))
    return out


def _analyze(value):
    if isinstance(value, Vec):
        if value.kind == "null":
            return _Num("empty", [])
        if value.kind == "integer":
            return _Num("integer", list(value.data), value.names)
        if value.kind == "logical":
            return _Num("logical", list(value.data), value.names)
        if value.kind == "double":
            return _Num("double", list(value.data), value.names)
        if value.kind == "complex":
            return _Num("complex", list(value.data), value.names)
        if value.kind == "factor":
            return _Num("factor", list(value.data))
        raise ValueError("non-numeric argument to binary operator")
    if isinstance(value, Factor):
        return _Num("factor", list(value.values))
    if value is None:
        return _Num("empty", [])
    if isinstance(value, bool):
        return _Num("logical", [value])
    if isinstance(value, int):
        return _Num("double", [float(value)])
    if isinstance(value, float):
        return _Num("double", [_clean_float(value)])
    if isinstance(value, complex):
        if math.isnan(value.real) or math.isnan(value.imag):
            return _Num("complex", [None])
        return _Num("complex", [complex(value)])
    if isinstance(value, dict):
        names = list(value)
        body = _analyze(list(value.values()))
        body.names = names
        return body
    if isinstance(value, np.ndarray):
        shape = tuple(int(dim) for dim in value.shape) if value.ndim > 1 else None
        flat = value.ravel(order="F") if value.ndim > 1 else value.ravel()
        if np.issubdtype(value.dtype, np.bool_):
            return _Num("logical", [bool(item) for item in flat.tolist()], shape=shape)
        if np.issubdtype(value.dtype, np.integer):
            items = [int(item) for item in flat.tolist()]
            if any(item < _INT_MIN or item > _INT_MAX for item in items):
                return _Num("double", [float(item) for item in items], shape=shape)
            return _Num("integer", items, shape=shape)
        if np.issubdtype(value.dtype, np.floating):
            return _Num("double", [_clean_float(item) for item in flat.tolist()], shape=shape)
        if np.issubdtype(value.dtype, np.complexfloating):
            data = []
            for item in flat.tolist():
                if math.isnan(item.real) or math.isnan(item.imag):
                    data.append(None)
                else:
                    data.append(complex(item))
            return _Num("complex", data, shape=shape)
        raise ValueError("non-numeric argument to binary operator")
    if isinstance(value, (list, tuple, range)):
        return _analyze_sequence(list(value))
    if isinstance(value, np.generic):
        return _analyze(np.atleast_1d(value))
    if isinstance(value, str):
        raise ValueError("non-numeric argument to binary operator")
    raise ValueError("non-numeric argument to binary operator")


def _analyze_sequence(items):
    if any(isinstance(item, Factor) for item in items):
        return _Num("factor", items)
    kinds = set()
    for item in items:
        if item is None or (isinstance(item, float) and math.isnan(item)):
            continue
        if isinstance(item, bool):
            kinds.add("logical")
        elif isinstance(item, int):
            kinds.add("double")
        elif isinstance(item, float):
            kinds.add("double")
        elif isinstance(item, complex):
            kinds.add("complex")
        else:
            raise ValueError("non-numeric argument to binary operator")
    if not kinds:
        return _Num("logical", [None] * len(items))
    if "complex" in kinds:
        data = []
        for item in items:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                data.append(None)
            elif isinstance(item, bool):
                data.append(complex(1.0 if item else 0.0))
            elif isinstance(item, complex) and (math.isnan(item.real) or math.isnan(item.imag)):
                data.append(None)
            else:
                data.append(complex(item))
        return _Num("complex", data)
    data = []
    for item in items:
        if item is None or (isinstance(item, float) and math.isnan(item)):
            data.append(None)
        elif isinstance(item, bool):
            data.append(1.0 if item else 0.0)
        else:
            data.append(float(item))
    if kinds == {"logical"}:
        logical = []
        for item in items:
            if item is None:
                logical.append(None)
            else:
                logical.append(bool(item))
        return _Num("logical", logical)
    return _Num("double", data)


def _expand(values, out_len):
    size = len(values)
    if out_len == 0:
        return values[:0]
    if size == out_len:
        return list(values)
    if size == 0:
        return []
    if out_len % size != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            RuntimeWarning,
            stacklevel=3,
        )
    reps, extra = divmod(out_len, size)
    return list(values) * reps + list(values)[:extra]


def _pair(left, right):
    n, m = len(left), len(right)
    if n == 0 or m == 0:
        length = 0
    else:
        length = max(n, m)
    if n == m:
        names = left.names if left.names is not None else right.names
    elif n > m:
        names = left.names
    else:
        names = right.names
    shape = None
    if left.shape is not None or right.shape is not None:
        if left.shape is not None and right.shape is not None and left.shape != right.shape:
            raise ValueError("non-conformable arrays")
        shape = left.shape if left.shape is not None else right.shape
        if shape is not None and int(np.prod(shape)) != length and length != 0:
            if min(n, m) not in (0, 1) and max(n, m) != int(np.prod(shape)):
                raise ValueError("non-conformable arrays")
    return _expand(left.values, length), _expand(right.values, length), names, shape


def _to_float(values):
    out = np.empty(len(values), dtype=np.float64)
    missing = np.zeros(len(values), dtype=bool)
    for index, value in enumerate(values):
        if value is None:
            out[index] = np.nan
            missing[index] = True
        else:
            out[index] = value
    return out, missing


def _compare_double(diff_missing, diff, tol_values):
    tol, tol_missing = _to_float(tol_values)
    with np.errstate(invalid="ignore"):
        less = np.abs(diff) < tol
    missing = diff_missing | tol_missing | np.isnan(diff)
    result = []
    for index, flag in enumerate(less):
        result.append(None if missing[index] else bool(flag))
    return result


def _integer_diff(left, right):
    out = []
    overflow = False
    for a, b in zip(left, right):
        if a is None or b is None:
            out.append(None)
            continue
        diff = int(a) - int(b)
        if diff < -2147483648 or diff > 2147483647:
            overflow = True
            out.append(None)
        else:
            out.append(diff)
    if overflow:
        warnings.warn("NAs produced by integer overflow", RuntimeWarning, stacklevel=3)
    abs_values = []
    for value in out:
        if value is None:
            abs_values.append(None)
        elif value == -2147483648:
            overflow = True
            abs_values.append(None)
        else:
            abs_values.append(abs(value))
    return abs_values


def near(x, y, tol=_MISSING):
    """True where `x` and `y` differ by strictly less than `tol`.

    `tol` defaults to the square root of double precision epsilon. `NA` and
    `NaN` stay missing, and `Inf` compared with `Inf` is missing because the
    difference is `NaN`.
    """
    if tol is _MISSING:
        tol = _SQRT_EPS
    left = _analyze(x)
    right = _analyze(y)
    bound = _analyze(tol)
    if "factor" in (left.kind, right.kind, bound.kind):
        warnings.warn("‘-’ not meaningful for factors", RuntimeWarning, stacklevel=2)
        xs, ys, names, shape = _pair(left, right)
        return Logical([None] * len(xs), names=names, shape=shape)
    xs, ys, names, shape = _pair(left, right)
    if len(xs) == 0:
        return Logical([], names=None, shape=shape)
    integer_like = {"integer", "logical"}
    if left.kind in integer_like and right.kind in integer_like:
        diff = _integer_diff(xs, ys)
        abs_expanded, tol_expanded, names, shape = _pair(
            _Num("double", diff, names=names, shape=shape),
            bound,
        )
        values, missing = _to_float(abs_expanded)
        tol_array, tol_missing = _to_float(tol_expanded)
        with np.errstate(invalid="ignore"):
            less = values < tol_array
        missing = missing | tol_missing | np.isnan(values) | np.isnan(tol_array)
        result = [None if missing[index] else bool(flag) for index, flag in enumerate(less)]
        return Logical(result, names=names, shape=shape)
    if "complex" in (left.kind, right.kind):
        def _complex(values, kind):
            out = []
            for value in values:
                if value is None:
                    out.append(None)
                elif kind == "logical":
                    out.append(complex(1.0 if value else 0.0))
                else:
                    out.append(complex(value))
            return out

        xs = _complex(xs, left.kind)
        ys = _complex(ys, right.kind)
        diff = []
        for a, b in zip(xs, ys):
            if a is None or b is None:
                diff.append(None)
            else:
                diff.append(abs(a - b))
        abs_expanded, tol_expanded, names, shape = _pair(
            _Num("double", diff, names=names, shape=shape),
            bound,
        )
        values, missing = _to_float(abs_expanded)
        tol_array, tol_missing = _to_float(tol_expanded)
        with np.errstate(invalid="ignore"):
            less = values < tol_array
        missing = missing | tol_missing | np.isnan(values) | np.isnan(tol_array)
        result = [None if missing[index] else bool(flag) for index, flag in enumerate(less)]
        return Logical(result, names=names, shape=shape)
    xs = _as_double_list(xs)
    ys = _as_double_list(ys)
    diff = []
    for a, b in zip(xs, ys):
        if a is None or b is None:
            diff.append(None)
        else:
            diff.append(abs(a - b))
    abs_expanded, tol_expanded, names, shape = _pair(
        _Num("double", diff, names=names, shape=shape),
        bound,
    )
    values, missing = _to_float(abs_expanded)
    tol_array, tol_missing = _to_float(tol_expanded)
    with np.errstate(invalid="ignore"):
        less = values < tol_array
    missing = missing | tol_missing | np.isnan(values) | np.isnan(tol_array)
    result = [None if missing[index] else bool(flag) for index, flag in enumerate(less)]
    return Logical(result, names=names, shape=shape)
