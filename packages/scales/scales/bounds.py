"""Rescale, rescale-mid, zero-range, censor, squish, and expand-range from scales 1.4.0 (R/bounds.R)."""

import datetime as _dt
import math
import sys
import warnings

try:
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None

# .Machine$double.eps
_EPS = sys.float_info.epsilon
_EPOCH = _dt.date(1970, 1, 1).toordinal()


class _NAType:
    """R's missing value, distinct from a plain NaN."""

    def __repr__(self):
        return "NA"


_NA = _NAType()


def _is_nan(value):
    return isinstance(value, float) and math.isnan(value)


def _is_missing(value):
    """R is.na is true for both NA and NaN."""
    return value is _NA or _is_nan(value)


def _unwrap(value):
    if _np is not None and isinstance(value, _np.generic):
        return value.item()
    return value


def _coerce(value, date_as_seconds=False, method="rescale"):
    value = _unwrap(value)
    if value is None or value is _NA:
        return _NA
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.timezone.utc)
        return float(value.timestamp())
    if isinstance(value, _dt.date):
        days = float(value.toordinal() - _EPOCH)
        # rescale_mid.Date is as.numeric(as.POSIXct(x)), seconds at UTC midnight.
        if date_as_seconds:
            return days * 86400.0
        return days
    if isinstance(value, str):
        raise ValueError(
            f"no applicable method for '{method}' applied to an object of class \"character\""
        )
    raise TypeError(f"non-numeric argument of type {type(value).__name__}")


def _elements(x, date_as_seconds=False, method="rescale"):
    if isinstance(x, (str, bytes)):
        raise ValueError(
            f"no applicable method for '{method}' applied to an object of class \"character\""
        )
    if _np is not None and isinstance(x, _np.ndarray):
        return [
            _coerce(value, date_as_seconds=date_as_seconds, method=method)
            for value in _np.asarray(x).ravel(order="F")
        ]
    if isinstance(x, (list, tuple)):
        return [
            _coerce(value, date_as_seconds=date_as_seconds, method=method)
            for value in x
        ]
    return [_coerce(x, date_as_seconds=date_as_seconds, method=method)]


def _export(value):
    if value is _NA:
        return None
    return value


def _export_vector(values):
    return [_export(value) for value in values]


def _is_tol_sequence(tol):
    if isinstance(tol, (list, tuple)):
        return True
    return _np is not None and isinstance(tol, _np.ndarray)


def _one_tol(diff, tol):
    tol = _unwrap(tol)
    if tol is None or tol is _NA or (isinstance(tol, float) and math.isnan(tol)):
        return None
    if isinstance(tol, bool):
        tol = float(tol)
    return bool(diff < float(tol))


def zero_range(x, tol=None):
    """True when the endpoints of x are not distinguishable from each other.

    x has length 1 or 2. The default tolerance is 1000 * .Machine$double.eps.
    Values are scaled by the smaller absolute endpoint before that comparison.
    A missing endpoint returns a missing logical. None inside x is R's NA.
    """
    if tol is None:
        tol = 1000.0 * _EPS
    if x is None:
        raise ValueError("`x` must be length 1 or 2")
    values = _elements(x)
    if len(values) == 1:
        return True
    if len(values) != 2:
        raise ValueError("`x` must be length 1 or 2")
    if _is_missing(values[0]) or _is_missing(values[1]):
        return None
    # Equal values, including signed zeros and infinite pairs.
    if values[0] == values[1]:
        return True
    if math.isinf(values[0]) or math.isinf(values[1]):
        return False
    scale = min(abs(values[0]), abs(values[1]))
    # Exactly one endpoint is zero: the other was not equal to it.
    if scale == 0.0:
        return False
    diff = abs((values[0] - values[1]) / scale)
    if _is_tol_sequence(tol):
        compared = [_one_tol(diff, item) for item in _elements(tol)]
        if len(compared) == 1:
            return compared[0]
        return compared
    return _one_tol(diff, tol)


def _range_finite(values):
    """range(x, na.rm = TRUE, finite = TRUE). Empty of finites is (Inf, -Inf)."""
    finite = [
        value
        for value in values
        if value is not _NA and not _is_nan(value) and not math.isinf(value)
    ]
    if not finite:
        return [math.inf, -math.inf]
    return [min(finite), max(finite)]


def _or_flag(left, right):
    """R's ||, including a missing logical and left-to-right stopping."""
    if left is True:
        return True
    if left is False:
        return right
    # Missing || TRUE is TRUE. Missing || FALSE and missing || missing stay missing.
    if right is True:
        return True
    return None


def _mean(values):
    if any(value is _NA for value in values):
        return _NA
    if any(_is_nan(value) for value in values):
        return float("nan")
    if not values:
        return float("nan")
    return sum(values) / len(values)


def _add(left, right):
    if left is _NA or right is _NA:
        return _NA
    return left + right


def _sub(left, right):
    if left is _NA or right is _NA:
        return _NA
    return left - right


def _mul(left, right):
    if left is _NA or right is _NA:
        return _NA
    return left * right


def _div(left, right):
    if left is _NA or right is _NA:
        return _NA
    return left / right


def rescale(x, to=(0.0, 1.0), from_=None, **kwargs):
    """Rescale x from one range onto another.

    None as x is NULL and returns None. None inside x is a missing number.
    A constant input, or a constant destination, becomes the mean of to,
    and both NA and NaN in x become missing on that path. Otherwise a NaN
    in x stays NaN. Dates are days since 1970-01-01. Datetimes are seconds.
    """
    if "from" in kwargs:
        if from_ is not None:
            raise TypeError("rescale() got multiple values for argument 'from'")
        from_ = kwargs.pop("from")
    if x is None:
        return None
    values = _elements(x)
    to_values = _elements(to)
    if from_ is None:
        from_values = _range_finite(values)
    else:
        from_values = _elements(from_)
    # || does not look at `to` once `from` is already a zero range.
    from_zero = zero_range(from_values)
    if from_zero is True:
        combined = True
    else:
        combined = _or_flag(from_zero, zero_range(to_values))
    if combined is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if combined:
        mid = _mean(to_values)
        return _export_vector([_NA if _is_missing(value) else mid for value in values])
    span_from = _sub(from_values[1], from_values[0])
    span_to = _sub(to_values[1], to_values[0])
    out = []
    for value in values:
        shifted = _sub(value, from_values[0])
        scaled = _div(shifted, span_from)
        out.append(_add(_mul(scaled, span_to), to_values[0]))
    return _export_vector(out)


_MISSING = object()
_POSIXCT = "\u201cPOSIXct\u201d"


def _is_time_input(x):
    if isinstance(x, (str, bytes)):
        return False
    if isinstance(x, _dt.date):
        return True
    if isinstance(x, (list, tuple)):
        return any(isinstance(value, _dt.date) for value in x)
    if _np is not None and isinstance(x, _np.ndarray) and x.dtype == object:
        return any(isinstance(value, _dt.date) for value in x.ravel(order="F"))
    return False


def _is_plain_numeric(obj):
    """R is.numeric. Logical and dates are not numeric."""
    if isinstance(obj, bool):
        return False
    if isinstance(obj, (int, float)):
        return True
    if _np is not None and isinstance(obj, _np.generic):
        return _is_plain_numeric(obj.item())
    if _np is not None and isinstance(obj, _np.ndarray):
        if obj.dtype == object:
            return all(_is_plain_numeric(value) for value in obj.ravel(order="F"))
        return _np.issubdtype(obj.dtype, _np.number)
    if isinstance(obj, (list, tuple)):
        return all(_is_plain_numeric(value) for value in obj)
    return False


def _contains_date(obj):
    if isinstance(obj, (str, bytes, bool, int, float)) or obj is None:
        return False
    if isinstance(obj, _dt.date):
        return True
    if isinstance(obj, (list, tuple)):
        return any(_contains_date(value) for value in obj)
    if _np is not None and isinstance(obj, _np.ndarray) and obj.dtype == object:
        return any(_contains_date(value) for value in obj.ravel(order="F"))
    return False


def _range_na_rm(values):
    """range(x, na.rm = TRUE). An empty set is (Inf, -Inf), with both warnings."""
    present = [
        value
        for value in values
        if value is not _NA and not _is_nan(value)
    ]
    if not present:
        warnings.warn(
            "no non-missing arguments to min; returning Inf",
            RuntimeWarning,
            stacklevel=2,
        )
        warnings.warn(
            "no non-missing arguments to max; returning -Inf",
            RuntimeWarning,
            stacklevel=2,
        )
        return [math.inf, -math.inf]
    return [min(present), max(present)]


def _align(left, right):
    """Recycle two vectors the way R's arithmetic does. A zero length wins."""
    if len(left) == 0 or len(right) == 0:
        return [], []
    n = max(len(left), len(right))
    uneven = (len(left) != n and n % len(left) != 0) or (
        len(right) != n and n % len(right) != 0
    )
    if uneven:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            RuntimeWarning,
            stacklevel=2,
        )

    def expand(values):
        if len(values) == n:
            return values
        return [values[i % len(values)] for i in range(n)]

    return expand(left), expand(right)


def _r_abs(value):
    if value is _NA:
        return _NA
    return abs(value)


def _r_max(values):
    """R max with na.rm FALSE. Empty warns and is -Inf. NA wins over NaN."""
    if len(values) == 0:
        warnings.warn(
            "no non-missing arguments to max; returning -Inf",
            RuntimeWarning,
            stacklevel=2,
        )
        return -math.inf
    if any(value is _NA for value in values):
        return _NA
    if any(_is_nan(value) for value in values):
        return float("nan")
    return max(values)


def _r_div(left, right):
    """R's double division. A zero divisor is signed Inf, and 0/0 is NaN."""
    if left is _NA or right is _NA:
        return _NA
    if (isinstance(left, float) and math.isnan(left)) or (
        isinstance(right, float) and math.isnan(right)
    ):
        return float("nan")
    if right == 0.0:
        if left == 0.0:
            return float("nan")
        sign = math.copysign(1.0, left) * math.copysign(1.0, right)
        if sign < 0.0:
            return float("-inf")
        return float("inf")
    return left / right


def _posix_error(argument):
    raise ValueError(
        f"do not know how to convert '{argument}' to class {_POSIXCT}"
    )


def _as_mid_numbers(obj, argument, as_time):
    if obj is None:
        return []
    if as_time and not _is_plain_numeric(obj):
        if not _is_time_input(obj):
            _posix_error(argument)
        return _elements(obj, date_as_seconds=True, method="rescale_mid")
    return _elements(obj, method="rescale_mid")


def _rescale_mid_numeric(values, to, from_values, mid_values, date_span):
    to_values = _elements(to, method="rescale_mid")
    from_zero = zero_range(from_values)
    if from_zero is True:
        combined = True
    else:
        combined = _or_flag(from_zero, zero_range(to_values))
    if combined is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if combined:
        center = _mean(to_values)
        return _export_vector(
            [_NA if _is_missing(value) else center for value in values]
        )
    # Date - number stays a Date, and abs() rejects it.
    if date_span:
        raise ValueError('abs not defined for "Date" objects')
    aligned_from, aligned_mid = _align(from_values, mid_values)
    distances = [
        _r_abs(_sub(left, right)) for left, right in zip(aligned_from, aligned_mid)
    ]
    extent = _mul(2.0, _r_max(distances))
    span = _sub(to_values[1], to_values[0])
    center = _mean(to_values)
    shifted_x, shifted_mid = _align(values, mid_values)
    out = []
    for left, right in zip(shifted_x, shifted_mid):
        moved = _sub(left, right)
        scaled = _r_div(moved, extent)
        out.append(_add(_mul(scaled, span), center))
    return _export_vector(out)


def rescale_mid(x, to=(0.0, 1.0), from_=None, mid=_MISSING, **kwargs):
    """Rescale x about a midpoint onto the range `to`.

    The midpoint lands on the mean of `to`. Both sides share one extent,
    twice the larger distance from `mid` to an end of `from`. `from`
    defaults to range(x) with missing values removed, so infinities stay.
    A constant input, or a constant destination, becomes the mean of `to`,
    and both NA and NaN become missing on that path. Otherwise a NaN stays
    NaN. None as x is NULL. None inside x, or a length-1 list of None, is a
    missing number. None as mid is NULL. Dates and datetimes are seconds
    since 1970-01-01 UTC, and a date has no default midpoint. A naive
    datetime is read as UTC.
    """
    if "from" in kwargs:
        if from_ is not None:
            raise TypeError("rescale_mid() got multiple values for argument 'from'")
        from_ = kwargs.pop("from")
    if x is None:
        return None
    time_input = _is_time_input(x)
    if time_input and mid is _MISSING:
        raise ValueError('argument "mid" is missing, with no default')
    date_span = (not time_input) and (
        _contains_date(from_) or (mid is not _MISSING and _contains_date(mid))
    )
    if mid is _MISSING:
        mid = 0.0
    if time_input:
        values = _elements(x, date_as_seconds=True, method="rescale_mid")
        if from_ is None:
            from_values = _range_na_rm(values)
        else:
            from_values = _as_mid_numbers(from_, "from", True)
        mid_values = _as_mid_numbers(mid, "mid", True)
    else:
        values = _elements(x, method="rescale_mid")
        if from_ is None:
            from_values = _range_na_rm(values)
        else:
            from_values = _elements(from_, method="rescale_mid")
        if mid is None:
            mid_values = []
        else:
            mid_values = _elements(mid, method="rescale_mid")
    return _rescale_mid_numeric(values, to, from_values, mid_values, date_span)


def _flag(value):
    if isinstance(value, (list, tuple)) or (
        _np is not None and isinstance(value, _np.ndarray)
    ):
        items = _elements(value)
        if len(items) == 0:
            raise ValueError("argument is of length zero")
        if len(items) > 1:
            raise ValueError("the condition has length > 1")
        value = items[0]
    else:
        value = _unwrap(value)
    if value is None or value is _NA or (isinstance(value, float) and math.isnan(value)):
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(value, str):
        raise ValueError("the condition has length > 1")
    return bool(value)


def _at(values, index):
    if index < 0 or index >= len(values):
        return _NA
    return values[index]


def _less(left, right):
    """R < . NA and NaN comparisons are missing, so the element is not replaced."""
    if left is _NA or right is _NA or _is_nan(left) or _is_nan(right):
        return _NA
    return left < right


def censor(x, range=(0.0, 1.0), only_finite=True, **kwargs):
    """Replace values outside range with NA.

    only_finite TRUE leaves non-finite values alone. FALSE also censors
    infinities. A comparison that is missing does not replace that element,
    so an existing NA or NaN stays. None as x is NULL and returns an empty
    list, matching censor(NULL). None inside x is a missing number.
    """
    if "only.finite" in kwargs:
        only_finite = kwargs.pop("only.finite")
    finite_only = _flag(only_finite)
    if x is None:
        return []
    values = _elements(x)
    limits = _elements(range)
    low = _at(limits, 0)
    high = _at(limits, 1)
    out = list(values)
    for index, value in enumerate(out):
        if finite_only and (
            value is _NA or _is_nan(value) or math.isinf(value)
        ):
            continue
        if _less(value, low) is True:
            out[index] = _NA
            value = _NA
        if _less(high, value) is True:
            out[index] = _NA
    return _export_vector(out)


def squish(x, range=(0.0, 1.0), only_finite=True, **kwargs):
    """Replace values outside range with the nearest limit.

    only_finite TRUE leaves non-finite values alone. FALSE also pulls
    infinities in to the nearest limit. The low side is applied first, then
    the high side sees that updated value, so an inverted range ends on the
    high limit. A comparison that is missing does not replace that element,
    so an existing NA or NaN stays. None as x is NULL and returns an empty
    list, matching squish(NULL). None inside x is a missing number.
    """
    if "only.finite" in kwargs:
        only_finite = kwargs.pop("only.finite")
    finite_only = _flag(only_finite)
    if x is None:
        return []
    values = _elements(x)
    # NULL and a length-zero range have no usable limit, so nothing is replaced.
    if range is None:
        limits = []
    else:
        limits = _elements(range)
    low = _at(limits, 0)
    high = _at(limits, 1)
    out = list(values)
    for index, value in enumerate(out):
        if finite_only and (
            value is _NA or _is_nan(value) or math.isinf(value)
        ):
            continue
        if _less(value, low) is True:
            out[index] = low
            value = low
        if _less(high, value) is True:
            out[index] = high
    return _export_vector(out)


def _numeric_arg(obj):
    """A scalar argument. None is NULL, an empty numeric, not a missing value."""
    if obj is None:
        return []
    return _elements(obj, method="expand_range")


def _binop(left, right, fn):
    left, right = _align(left, right)
    return [fn(a, b) for a, b in zip(left, right)]


def expand_range(range, mul=0, add=0, zero_width=1):
    """Expand the endpoints of a range by a multiple of its width plus a constant.

    The distance is `zero_width` when the endpoints are a zero range, and
    `diff(range)` otherwise. Each end then moves by `width * mul + add`,
    the lower end backward and the upper end forward. None as range is
    NULL and returns None. None as mul, add, or zero_width is NULL and the
    result is empty. None inside a vector is a missing number. A missing
    endpoint makes the zero-range test missing, which is an error. A
    length-1 range counts as zero-width and is recycled to two endpoints.
    """
    if range is None:
        return None
    flag = zero_range(range)
    if flag is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if flag is not True and flag is not False:
        raise ValueError("the condition has length > 1")
    values = _elements(range, method="expand_range")
    if flag:
        width = _numeric_arg(zero_width)
    else:
        width = [_sub(values[1], values[0])]
    # (width * mul + add), then c(-1, 1) times that, then added to range.
    pad = _binop(_binop(width, _numeric_arg(mul), _mul), _numeric_arg(add), _add)
    delta = _binop([-1.0, 1.0], pad, _mul)
    return _export_vector(_binop(values, delta, _add))
