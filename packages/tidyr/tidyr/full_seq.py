"""full_seq: fill a numeric, Date, or POSIXct vector out to its period.

The numeric method checks that every observation sits within ``tol`` of the
grid that starts at the minimum and steps by ``period``. It then calls the
same ``seq(from, to, by=)`` rule as R, after extending the end by ``tol``
when that end is already within ``tol`` of the next grid point. Date and
POSIXct convert with ``as.numeric``, run that method, and put the original
attributes back with R's ``mostattributes<-``.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np

_ABSENT = object()
_INTEGER_MAX = 2147483647
_EPS = float(np.finfo(np.float64).eps)
_DROP_ATTRS = ("class",)


def _no_method(kind: str) -> None:
    raise ValueError(
        f'no applicable method for \'full_seq\' applied to an object of class "{kind}"'
    )


def _fmt_num(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0:
        return "0"
    if math.isfinite(value) and abs(value) < 1e16 and float(value).is_integer():
        return str(int(value))
    return repr(float(value))


def _bounds_what(what: str, value: float, min_value, max_value) -> str:
    low = -math.inf if min_value is None else float(min_value)
    high = math.inf if max_value is None else float(max_value)
    if math.isfinite(low) and math.isfinite(high):
        return f"{what} between {_fmt_num(low)} and {_fmt_num(high)}"
    if value < low:
        return f"{what} larger than or equal to {_fmt_num(low)}"
    if value > high:
        return f"{what} smaller than or equal to {_fmt_num(high)}"
    raise ValueError("Unexpected state in OOB check")


def _fail_number(arg: str, what: str, detail: str) -> None:
    raise ValueError(f"`{arg}` must be {what}, not {detail}.")


def check_number_decimal(
    x: Any,
    *,
    arg: str,
    min_value: float | None = None,
    max_value: float | None = None,
    allow_infinite: bool = True,
) -> tuple[float, bool]:
    """rlang ``check_number_decimal``. Returns ``(value, is_integer)``."""
    if x is _ABSENT:
        _fail_number(arg, "a number", "absent")
    if x is None:
        _fail_number(arg, "a number", "`NULL`")
    if isinstance(x, (bool, np.bool_)):
        _fail_number(arg, "a number", "`TRUE`" if bool(x) else "`FALSE`")
    if isinstance(x, str):
        _fail_number(arg, "a number", f'the string "{x}"')
    if isinstance(x, complex):
        _fail_number(arg, "a number", f"the complex number {x}")
    if isinstance(x, np.ndarray):
        if x.dtype == np.bool_:
            _fail_number(arg, "a number", "`TRUE`" if x.size == 1 and bool(x) else "a logical vector")
        if x.size == 0:
            kind = "an empty integer vector" if np.issubdtype(x.dtype, np.integer) else "an empty numeric vector"
            _fail_number(arg, "a number", kind)
        if x.size != 1:
            kind = "an integer vector" if np.issubdtype(x.dtype, np.integer) else "a double vector"
            _fail_number(arg, "a number", kind)
        x = x.reshape(-1)[0]
    elif isinstance(x, (list, tuple)):
        if len(x) == 0:
            _fail_number(arg, "a number", "an empty numeric vector")
        if len(x) != 1:
            integral = all(isinstance(item, (int, np.integer)) and not isinstance(item, bool) for item in x)
            _fail_number(arg, "a number", "an integer vector" if integral else "a double vector")
        x = x[0]
    if isinstance(x, (bool, np.bool_)):
        _fail_number(arg, "a number", "`TRUE`" if bool(x) else "`FALSE`")
    if isinstance(x, (int, np.integer)):
        value = int(x)
        number = float(value)
        is_integer = True
    elif isinstance(x, (float, np.floating)):
        number = float(x)
        is_integer = False
        value = number
        if math.isnan(number):
            _fail_number(arg, "a number", "`NaN`")
    else:
        _fail_number(arg, "a number", f"a {type(x).__name__}")
    if math.isinf(number) and not allow_infinite:
        _fail_number(arg, "a number", f"the number {_fmt_num(number)}")
    low = -math.inf if min_value is None else float(min_value)
    high = math.inf if max_value is None else float(max_value)
    if number < low or number > high:
        what = _bounds_what("a number", number, min_value, max_value)
        _fail_number(arg, what, f"the number {_fmt_num(number)}")
    if is_integer and (value > _INTEGER_MAX or value < -_INTEGER_MAX):
        return number, False
    return number, is_integer


def _is_na_real(value: float) -> bool:
    return math.isnan(value)


def _as_numeric_vector(x: Any) -> tuple[np.ndarray, bool]:
    """Return ``(values, integer_storage)``. Missing values are NaN."""
    if isinstance(x, (bool, np.bool_)):
        _no_method("logical")
    if isinstance(x, str):
        _no_method("character")
    if x is None:
        _no_method("NULL")
    if isinstance(x, (int, np.integer)):
        value = int(x)
        if value > _INTEGER_MAX or value < -_INTEGER_MAX:
            return np.array([value], dtype=np.float64), False
        return np.array([value], dtype=np.int64), True
    if isinstance(x, (float, np.floating)):
        return np.array([float(x)], dtype=np.float64), False
    if isinstance(x, np.ndarray):
        if x.dtype == np.bool_:
            _no_method("logical")
        if x.dtype.kind in "SU":
            _no_method("character")
        if np.issubdtype(x.dtype, np.integer):
            flat = np.array(x, dtype=np.int64, copy=True).reshape(-1)
            if flat.size and (np.any(flat > _INTEGER_MAX) or np.any(flat < -_INTEGER_MAX)):
                return flat.astype(np.float64), False
            return flat, True
        if np.issubdtype(x.dtype, np.floating):
            return np.array(x, dtype=np.float64, copy=True).reshape(-1), False
        _no_method("list")
    if isinstance(x, (list, tuple)):
        if any(isinstance(item, str) for item in x):
            _no_method("character")
        if x and all(isinstance(item, (bool, np.bool_)) for item in x):
            _no_method("logical")
        if any(isinstance(item, (list, tuple, dict)) for item in x):
            _no_method("list")
        integer = True
        values: list[float] = []
        for item in x:
            if item is None:
                integer = False
                values.append(math.nan)
            elif isinstance(item, (bool, np.bool_)):
                _no_method("logical")
            elif isinstance(item, (int, np.integer)):
                value = int(item)
                if value > _INTEGER_MAX or value < -_INTEGER_MAX:
                    integer = False
                values.append(float(value))
            elif isinstance(item, (float, np.floating)):
                integer = False
                values.append(float(item))
            else:
                _no_method("list")
        if integer:
            return np.array([int(value) for value in values], dtype=np.int64), True
        return np.array(values, dtype=np.float64), False
    _no_method("list")


def _kept(attributes: dict | None) -> dict:
    if not attributes:
        return {}
    return {key: value for key, value in attributes.items() if key not in _DROP_ATTRS}


def _as_dim(dim: Any) -> list[int] | None:
    if isinstance(dim, (str, bytes)):
        return None
    try:
        dims = [int(item) for item in dim]
    except (TypeError, ValueError):
        return None
    if not dims or any(item < 0 for item in dims):
        return None
    return dims


def _dimnames_fit(dims: list[int], dimnames: Any) -> bool:
    if isinstance(dimnames, (str, bytes)) or not isinstance(dimnames, (list, tuple)):
        return False
    if len(dimnames) != len(dims):
        return False
    for extent, names in zip(dims, dimnames):
        if names is None:
            continue
        try:
            size = len(names)
        except TypeError:
            return False
        if isinstance(names, (str, bytes)) or size != extent:
            return False
    return True


def _mostattributes(length: int, attributes: dict | None) -> dict:
    """R ``mostattributes<-`` onto a vector of ``length``.

    ``dim`` is copied only when its product is ``length``. That assignment
    clears ``names``. ``names`` are copied only when ``dim`` was not copied
    and the name vector has the same length. ``dimnames`` are copied only
    after a valid ``dim``, and only when each component is ``NULL`` or has
    that dimension's extent.
    """
    if not attributes:
        return {}
    kept: dict = {}
    names: Any = _ABSENT
    dim: Any = _ABSENT
    dimnames: Any = _ABSENT
    for key, value in attributes.items():
        if key == "names":
            names = value
        elif key == "dim":
            dim = value
        elif key == "dimnames":
            dimnames = value
        elif key != "class":
            kept[key] = value
    dims = None if dim is _ABSENT or dim is None else _as_dim(dim)
    dim_ok = False
    if dims is not None:
        product = 1
        for item in dims:
            product *= item
        if product == length:
            kept["dim"] = dims
            dim_ok = True
    if (
        not dim_ok
        and names is not _ABSENT
        and names is not None
        and not isinstance(names, (str, bytes))
    ):
        try:
            name_len = len(names)
        except TypeError:
            name_len = -1
        if name_len == length:
            kept["names"] = names
    if dim_ok and dimnames is not _ABSENT and dimnames is not None and dims is not None:
        if _dimnames_fit(dims, dimnames):
            kept["dimnames"] = dimnames
    return kept


class Date:
    """R Date: days since 1970-01-01, stored as double."""

    classes = ("Date",)

    def __init__(self, days: Any, attributes: dict | None = None):
        self.days = np.array(days, dtype=np.float64, copy=True).reshape(-1)
        self.attributes = _kept(attributes)

    def __len__(self) -> int:
        return int(self.days.size)


class POSIXct:
    """R POSIXct: seconds since 1970-01-01 UTC, with an optional tzone."""

    classes = ("POSIXct", "POSIXt")

    def __init__(self, seconds: Any, tzone: Any = _ABSENT, attributes: dict | None = None):
        self.seconds = np.array(seconds, dtype=np.float64, copy=True).reshape(-1)
        self.tzone = tzone
        self.attributes = _kept(attributes)

    def __len__(self) -> int:
        return int(self.seconds.size)


def _as_r_integer(value: float) -> int:
    if (not math.isfinite(value)) or value > _INTEGER_MAX or value < -_INTEGER_MAX:
        warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=3)
        raise ValueError("NA/NaN argument")
    return int(math.trunc(value))


def _seq_integer(from_: int, to: int, by: int) -> np.ndarray:
    del_ = float(to) - float(from_)
    if del_ == 0.0 and to == 0:
        return np.array([to], dtype=np.int32)
    number = del_ / float(by)
    if not math.isfinite(number):
        if by == 0 and del_ == 0.0:
            return np.array([from_], dtype=np.int32)
        raise ValueError("invalid '(to - from)/by'")
    if number < 0.0:
        raise ValueError("wrong sign in 'by' argument")
    if number > _INTEGER_MAX:
        raise ValueError("'by' argument is much too small")
    scale = max(abs(to), abs(from_))
    if math.isfinite(del_) and abs(del_) / float(scale) < 100.0 * _EPS:
        return np.array([from_], dtype=np.int32)
    count = _as_r_integer(number)
    if count >= 2:
        wide = np.empty(count + 1, dtype=np.int64)
        wide[0] = from_
        wide[1:] = by
        np.cumsum(wide, out=wide)
        if np.any(wide > _INTEGER_MAX) or np.any(wide < -_INTEGER_MAX):
            warnings.warn("NAs produced by integer overflow", RuntimeWarning, stacklevel=3)
            first = int(np.flatnonzero((wide > _INTEGER_MAX) | (wide < -_INTEGER_MAX))[0])
            out = wide.astype(np.float64)
            out[first:] = np.nan
            return out
        return wide.astype(np.int32)
    out = np.empty(count + 1, dtype=np.int32)
    for index in range(count + 1):
        product = int(index) * int(by)
        total = int(from_) + product
        if product > _INTEGER_MAX or product < -_INTEGER_MAX or total > _INTEGER_MAX or total < -_INTEGER_MAX:
            warnings.warn("NAs produced by integer overflow", RuntimeWarning, stacklevel=3)
            floated = out.astype(np.float64)
            floated[index:] = np.nan
            return floated
        out[index] = total
    return out


def _seq_double(from_: float, to: float, by: float) -> np.ndarray:
    if not math.isfinite(from_):
        raise ValueError("'from' must be a finite number")
    if not math.isfinite(to):
        raise ValueError("'to' must be a finite number")
    del_ = to - from_
    finite_del = math.isfinite(del_)
    if del_ == 0.0 and to == 0.0:
        return np.array([to], dtype=np.float64)
    number = del_ / by if finite_del else to / by - from_ / by
    if not math.isfinite(number):
        if by == 0.0 and del_ == 0.0:
            return np.array([from_], dtype=np.float64)
        raise ValueError("invalid '(to - from)/by'")
    if number < 0.0:
        raise ValueError("wrong sign in 'by' argument")
    if number > _INTEGER_MAX:
        raise ValueError("'by' argument is much too small")
    scale = max(abs(to), abs(from_))
    if finite_del and abs(del_) / scale < 100.0 * _EPS:
        return np.array([from_], dtype=np.float64)
    count = _as_r_integer(number + 1e-10)
    index = np.arange(0, count + 1, dtype=np.float64)
    if finite_del:
        values = from_ + index * by
    else:
        values = (from_ / 4.0 + index * (by / 4.0)) * 4.0
    if by > 0.0:
        return np.minimum(values, to)
    return np.maximum(values, to)


def _range_numeric(values: np.ndarray) -> tuple[float, float]:
    # Inf is observed. NaN, including R's NA, is not. Integers have no NaN.
    if np.issubdtype(values.dtype, np.integer):
        kept = values
    else:
        kept = values[~np.isnan(values)]
    if kept.size == 0:
        warnings.warn(
            "no non-missing arguments to min; returning Inf",
            RuntimeWarning,
            stacklevel=3,
        )
        warnings.warn(
            "no non-missing arguments to max; returning -Inf",
            RuntimeWarning,
            stacklevel=3,
        )
        return math.inf, -math.inf
    return float(np.min(kept)), float(np.max(kept))


def _r_mod(values: np.ndarray, period: float) -> np.ndarray:
    # R's %% matches NumPy's remainder, including a finite value modulo Inf.
    # NumPy also warns when the remainder is NaN; R does not.
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.mod(np.asarray(values, dtype=np.float64), np.float64(period))


def _reject_irregular(values: np.ndarray, origin: float, period: float, tol: float) -> None:
    rem = _r_mod(values.astype(np.float64) - np.float64(origin), period)
    distance = np.float64(period) - rem
    # NaN comparisons are missing. Inf comparisons are not: Inf > tol is TRUE.
    rem_missing = np.isnan(rem)
    distance_missing = np.isnan(distance)
    left_true = ~rem_missing & (rem > tol)
    right_true = ~distance_missing & (distance > tol)
    left_false = ~rem_missing & ~left_true
    right_false = ~distance_missing & ~right_true
    if np.any(left_true & right_true):
        raise ValueError("`x` is not a regular sequence.")
    if np.any(~(left_false | right_false)):
        raise ValueError("missing value where TRUE/FALSE needed")


def _full_seq_numeric(x: Any, period: Any, tol: Any) -> np.ndarray:
    period_value, period_is_int = check_number_decimal(period, arg="period")
    tol_value, tol_is_int = check_number_decimal(tol, arg="tol", min_value=0.0)
    values, values_are_int = _as_numeric_vector(x)
    origin, end = _range_numeric(values)
    origin_is_int = values_are_int and math.isfinite(origin) and float(origin).is_integer()
    end_is_int = values_are_int and math.isfinite(end) and float(end).is_integer()
    if origin_is_int:
        origin = int(origin)
    if end_is_int:
        end = int(end)
    _reject_irregular(values, float(origin), period_value, tol_value)
    end_rem = float(_r_mod(np.float64(end) - np.float64(origin), period_value))
    gap = period_value - end_rem
    if not math.isfinite(gap):
        raise ValueError("missing value where TRUE/FALSE needed")
    if gap <= tol_value:
        if end_is_int and tol_is_int:
            total = int(end) + int(tol_value)
            if total > _INTEGER_MAX or total < -_INTEGER_MAX:
                warnings.warn("NAs produced by integer overflow", RuntimeWarning, stacklevel=2)
                end = math.nan
                end_is_int = False
            else:
                end = total
        else:
            end = float(end) + tol_value
            end_is_int = False
    if values_are_int and origin_is_int and end_is_int and period_is_int:
        return _seq_integer(int(origin), int(end), int(period_value))
    return _seq_double(float(origin), float(end), float(period_value))


def full_seq(x: Any, period: Any = _ABSENT, tol: Any = 1e-6):
    """Fill ``x`` from its minimum to its maximum in steps of ``period``.

    ``x`` is a numeric vector, a :class:`Date`, or a :class:`POSIXct`.
    ``tol`` is the largest distance from the grid that still counts as regular.
    """
    if isinstance(x, Date):
        values = _full_seq_numeric(x.days, period, tol)
        return Date(values, attributes=_mostattributes(int(values.size), x.attributes))
    if isinstance(x, POSIXct):
        values = _full_seq_numeric(x.seconds, period, tol)
        return POSIXct(
            values,
            tzone=x.tzone,
            attributes=_mostattributes(int(values.size), x.attributes),
        )
    return _full_seq_numeric(x, period, tol)
