"""between and %between%, with the integer, double, and character kernel in Rust."""

from __future__ import annotations

import math

import datatable_core

from datatable._util import (
    NA_INTEGER,
    DataTableError,
    as_sequence,
    is_integer64,
    is_na,
)

def _flag(value, name: str) -> bool:
    if isinstance(value, (bool,)) and not isinstance(value, int):
        pass
    if value is True:
        return True
    if value is False:
        return False
    raise DataTableError(f"{name} must be TRUE or FALSE")


def _na_bounds(value) -> bool:
    if value is True:
        return True
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    raise DataTableError("NAbounds must be TRUE or NA")


def _logical_x(values) -> bool:
    return bool(values) and all(isinstance(item, (bool,)) and not is_na(item) for item in values)


def _looks_logical(values) -> bool:
    if not values:
        return False
    for item in values:
        if is_na(item):
            continue
        if not isinstance(item, (bool,)):
            return False
    return any(isinstance(item, (bool,)) for item in values)


def _as_i32(values):
    out = []
    for item in values:
        if is_na(item):
            out.append(NA_INTEGER)
            continue
        if isinstance(item, bool):
            out.append(int(item))
            continue
        number = int(item)
        if number < -2147483648 or number > 2147483647:
            return None
        out.append(number)
    return out


def _fits_i32_number(item) -> bool:
    if is_na(item):
        return True
    if isinstance(item, bool):
        return True
    if isinstance(item, int):
        return -2147483648 <= item <= 2147483647
    if isinstance(item, float):
        if not math.isfinite(item):
            return False
        return item == math.trunc(item) and -2147483648 <= item <= 2147483647
    return False


def _as_f64(values):
    out = []
    for item in values:
        if is_na(item):
            out.append(float("nan"))
        elif isinstance(item, bool):
            out.append(float(int(item)))
        else:
            out.append(float(item))
    return out


def _as_str(values):
    out = []
    for item in values:
        if is_na(item):
            out.append(None)
        else:
            out.append(str(item))
    return out


def _kind(values) -> str:
    if any(isinstance(item, str) for item in values):
        return "character"
    if any(isinstance(item, float) for item in values):
        return "double"
    return "integer"


def _decode(codes):
    return [None if code < 0 else bool(code) for code in codes]


def between(x, lower, upper, incbounds=True, NAbounds=True, check=False, ignore_tzone=False):
    """Is each x[i] between lower and upper. ignore_tzone is accepted for the POSIXct path."""
    del ignore_tzone
    if is_integer64(x) or is_integer64(lower) or is_integer64(upper):
        raise DataTableError("trying to use integer64 class when 'bit64' package is not installed")
    xs = as_sequence(x)
    ls = as_sequence(lower)
    us = as_sequence(upper)
    if isinstance(xs, type(x)) and hasattr(xs, "ndim"):
        raise DataTableError("between has been passed an argument x of type logical")
    if getattr(xs, "ndim", 1) > 1:
        xs = list(xs.reshape(-1, order="F"))
    if _looks_logical(xs) and any(isinstance(item, bool) for item in xs):
        raise DataTableError("between has been passed an argument x of type logical")
    if _looks_logical(ls):
        ls = [None if is_na(item) else int(item) for item in ls]
    if _looks_logical(us):
        us = [None if is_na(item) else int(item) for item in us]
    open_bounds = not _flag(incbounds, "incbounds")
    na_bounds = _na_bounds(NAbounds)
    do_check = _flag(check, "check")
    kind = _kind(xs + ls + us)
    try:
        if kind == "character":
            codes = datatable_core.between_str_py(
                _as_str(xs), _as_str(ls), _as_str(us), open_bounds, na_bounds, do_check
            )
        elif kind == "double" or not all(_fits_i32_number(item) for item in xs + ls + us):
            codes = datatable_core.between_f64_py(
                _as_f64(xs), _as_f64(ls), _as_f64(us), open_bounds, na_bounds, do_check
            )
        else:
            xi = _as_i32(xs)
            li = _as_i32(ls)
            ui = _as_i32(us)
            codes = datatable_core.between_i32_py(xi, li, ui, open_bounds, na_bounds, do_check)
    except RuntimeError as exc:
        raise DataTableError(str(exc)) from None
    return _decode(codes)


def between_op(x, y):
    """%between%. y is the lower bound then the upper bound."""
    ys = as_sequence(y)
    if len(ys) != 2:
        raise DataTableError(
            f"RHS has length() {len(ys)}; expecting length 2. "
            "The first element should be the lower bound(s); the second element should be the upper bound(s)."
        )
    return between(x, ys[0], ys[1], incbounds=True)
