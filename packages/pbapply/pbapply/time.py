"""Format one length of time the way pbapply's getTimeAsString does.

The R function is base arithmetic: ``%%``, ``round``, ``floor``, and
``sprintf``. Sixty seconds are not carried into the next minute.
"""

from __future__ import annotations

import math
import warnings

_BAD_FORMAT = "invalid format '%02i'; use format %f, %e, %g or %a for numeric objects"
_MISSING = "missing value where TRUE/FALSE needed"
_INT_MIN = -2147483648
_INT_MAX = 2147483647
# R warns once ``abs(x / y)`` passes 2^63, then keeps going.
_MODULUS_WARN = 2.0**63
# Above 2^125 the double subtraction R falls back to has lost the remainder.
_MODULUS_SPLIT = 2.0**125


def getTimeAsString(time):
    """Format one time in seconds as ``DDd HHh MMm SSs``.

    ``None`` is R's ``NULL`` and returns ``"calculating"``. ``inf`` and
    ``-inf`` both return ``"Inf"``. A missing number raises ``ValueError``.
    A list or tuple is an atomic vector: length 0 and length greater than 1
    are errors, and one element is unwrapped.
    """
    if isinstance(time, (list, tuple)):
        if len(time) > 1:
            raise ValueError("length of input must be 1")
        if len(time) == 0:
            raise ValueError("argument is of length zero")
        time = time[0]
    if time is None:
        return "calculating"
    if isinstance(time, bool):
        time = float(time)
    elif isinstance(time, (int, float)):
        time = float(time)
    else:
        raise ValueError("non-numeric argument to binary operator")
    if math.isinf(time):
        return "Inf"

    seconds = _round(_mod(time, 60.0))
    minutes_total = _floor(time / 60.0)
    minutes = _floor(_mod(minutes_total, 60.0))
    hours_total = _floor(minutes_total / 60.0)
    days = _floor(hours_total / 24.0)
    hours = _floor(_mod(_floor(_mod(hours_total, 24.0)), 60.0))

    text = ""
    if _positive(days):
        text = _sprintf(days, "d ")
    if _positive(hours) or _positive(days):
        text += _sprintf(hours, "h ")
    if _positive(minutes) or _positive(hours) or _positive(days):
        text += _sprintf(minutes, "m ")
    return text + _sprintf(seconds, "s")


def _positive(value):
    """R ``if (value > 0)``. A missing value is an error, not false."""
    if math.isnan(value):
        raise ValueError(_MISSING)
    return value > 0


def _floor(value):
    if not math.isfinite(value):
        return value
    return float(math.floor(value))


def _round(value):
    """R ``round`` with digits 0. Ties go to the even integer, and ``-0`` stays signed."""
    if math.isnan(value) or math.isinf(value) or value == 0.0:
        return math.copysign(0.0, value) if value == 0.0 else value
    magnitude = abs(value)
    down = math.floor(magnitude)
    fraction = magnitude - down
    if fraction > 0.5:
        rounded = down + 1.0
    elif fraction < 0.5:
        rounded = down
    elif math.fmod(down, 2.0) == 0.0:
        rounded = down
    else:
        rounded = down + 1.0
    if rounded == 0.0:
        return math.copysign(0.0, value)
    return math.copysign(rounded, value)


def _mod(x, y):
    """One R ``%%`` of two doubles.

    A negative no larger than half a long-double ulp of ``y`` collapses to 0
    where Python's remainder is ``y``. At and above 2^125 the remainder R
    keeps is the double subtraction, or 0 when that subtraction has left the
    range.
    """
    if not math.isfinite(x) or not math.isfinite(y) or y == 0.0:
        return math.nan
    quotient = x / y
    if not math.isfinite(quotient):
        return math.nan
    if abs(quotient) > _MODULUS_WARN:
        warnings.warn(
            "probable complete loss of accuracy in modulus",
            RuntimeWarning,
            stacklevel=2,
        )
    if abs(x) >= _MODULUS_SPLIT:
        naive = x - math.floor(quotient) * y
        if not math.isfinite(naive) or naive < 0.0 or naive >= y:
            return 0.0
        return float(naive)
    result = x % y
    if result == y and math.floor(quotient) == -1 and abs(x) <= _half_ulp_long_double(y):
        return 0.0
    return result


def _half_ulp_long_double(y):
    """Half the 80-bit ulp of ``y``. ``frexp``'s exponent is one past the leading bit."""
    _mantissa, exponent = math.frexp(abs(y))
    return 2.0 ** (exponent - 65)


def _sprintf(value, suffix):
    """R ``sprintf("%02i", value)`` plus ``suffix``. The number must fit in a 32-bit int."""
    if not math.isfinite(value) or value != math.trunc(value):
        raise ValueError(_BAD_FORMAT)
    as_int = int(value)
    if as_int < _INT_MIN or as_int > _INT_MAX:
        raise ValueError(_BAD_FORMAT)
    return f"{as_int:02d}{suffix}"
