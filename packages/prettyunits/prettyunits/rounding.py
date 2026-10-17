"""Fixed and significant rounding that keeps trailing zeros."""

import math

from prettyunits._r import format_fixed, format_integer, r_round


def pretty_round(x, digits=0, sci_range=math.inf, sci_sep="e"):
    """Round to decimal places and print trailing zeros.

    A number returns a string. A list returns a list of strings. ``None`` is
    R's NA and is printed as ``"NA"``. ``float("nan")`` is printed as
    ``"NaN"`` because R writes ``"NA"`` for ``is.na`` and then overwrites
    NaN and Inf with ``as.character``.
    """
    values, scalar = _as_values(x)
    places = _as_digits(digits)
    if len(places) != 1 and len(places) != len(values):
        raise ValueError(
            "digits must either be a scalar or the same length as x"
        )
    if any(isinstance(place, bool) for place in places):
        raise ValueError("bool is not numeric")
    _require_range(sci_range)
    _require_separator(sci_sep)
    if len(places) == 1:
        place = places[0]
        # R 4.5 calls formatC(digits = digits + logval) on every scientific
        # value at once, and formatC fails when that digits vector has
        # length above one.
        scientific = sum(1 for value in values if _is_scientific(value, place, sci_range))
        if scientific >= 2:
            raise ValueError("the condition has length > 1")
        out = [_round_one(value, place, sci_range, sci_sep) for value in values]
    else:
        out = [
            _round_one(value, place, sci_range, sci_sep)
            for value, place in zip(values, places)
        ]
    if scalar:
        return out[0]
    return out


def pretty_signif(x, digits=6, sci_range=6, sci_sep="e"):
    """Round to significant digits, then print with ``pretty_round``."""
    values, scalar = _as_values(x)
    if isinstance(digits, bool) or not isinstance(digits, (int, float)):
        if isinstance(digits, bool):
            raise ValueError("bool is not numeric")
        raise ValueError("digits must be numeric")
    _require_range(sci_range)
    _require_separator(sci_sep)
    out = [None] * len(values)
    finite_at = []
    finite = []
    for index, value in enumerate(values):
        kind, number = _classify(value)
        if kind == "missing":
            out[index] = "NA"
        elif kind == "nan":
            out[index] = "NaN"
        elif kind == "inf":
            out[index] = "Inf" if number > 0.0 else "-Inf"
        else:
            finite_at.append(index)
            finite.append(number)
    if finite:
        places = _significant_places(finite, digits)
        printed = pretty_round(
            finite, digits=places, sci_range=sci_range, sci_sep=sci_sep
        )
        for index, text in zip(finite_at, printed):
            out[index] = text
    if scalar:
        return out[0]
    return out


def _round_one(value, digits, sci_range, sci_sep):
    kind, number = _classify(value)
    if kind == "missing":
        return "NA"
    if kind == "nan":
        return "NaN"
    if kind == "inf":
        return "Inf" if number > 0.0 else "-Inf"
    _require_digit(digits)
    rounded = r_round(number, digits)
    if _uses_scientific(rounded, sci_range):
        logval = math.floor(math.log10(abs(rounded)))
        mantissa = _divide(rounded, 10.0 ** logval)
        return (
            format_fixed(mantissa, digits + logval)
            + sci_sep
            + format_integer(logval)
        )
    shown = 0 if digits < 0 else digits
    return format_fixed(rounded, shown)


def _is_scientific(value, digits, sci_range):
    """True when pretty_round would print `value` in scientific notation."""
    kind, number = _classify(value)
    if kind != "number":
        return False
    _require_digit(digits)
    return _uses_scientific(r_round(number, digits), sci_range)


def _divide(numerator, denominator):
    """IEEE division. `10^logval` underflows to 0 for denormal values, and R gives Inf."""
    if denominator == 0.0:
        return math.copysign(math.inf, numerator)
    return numerator / denominator


def _uses_scientific(rounded, sci_range):
    """Non-zero values whose order of magnitude reaches ``sci_range``.

    Positive infinity never selects scientific notation. The comparison is
    ``>=``, matching ``rounding.R`` rather than the manual's ``>``.
    """
    if rounded == 0.0 or (math.isinf(sci_range) and sci_range > 0):
        return False
    return abs(math.log10(abs(rounded))) >= sci_range


def _significant_places(values, digits):
    """Decimal places that leave ``digits`` significant digits.

    ``(toplog %% 1) %in% 0`` is exact equality of the modulo with 0.
    """
    bottom = [None] * len(values)
    toplog = []
    for index, value in enumerate(values):
        if value == 0.0:
            bottom[index] = digits
            toplog.append(float("-inf"))
        else:
            toplog.append(math.log10(abs(value)))
    toplog = [_ceil_log(power) for power in toplog]
    for index, place in enumerate(bottom):
        if place is None:
            bottom[index] = digits - toplog[index]
    revised = []
    for value, place in zip(values, bottom):
        rounded = r_round(value, place)
        if rounded == 0.0:
            revised.append(float("-inf"))
        else:
            revised.append(math.log10(abs(rounded)))
    revised = [_ceil_log(power) for power in revised]
    for index, power in enumerate(toplog):
        if power < revised[index]:
            bottom[index] -= 1
    return bottom


def _ceil_log(power):
    """R's exact-log adjustment, then ``ceiling``."""
    if math.isnan(power) or math.isinf(power):
        return power
    if power % 1.0 == 0.0:
        power += 1.0
    return float(math.ceil(power))


def _as_values(x):
    if isinstance(x, (list, tuple)):
        return list(x), False
    return [x], True


def _as_digits(digits):
    if isinstance(digits, (list, tuple)):
        return list(digits)
    return [digits]


def _classify(value):
    if value is None:
        return "missing", None
    if isinstance(value, bool):
        raise ValueError("bool is not numeric")
    if not isinstance(value, (int, float)):
        raise ValueError("x must be numeric")
    number = float(value)
    if math.isnan(number):
        return "nan", number
    if math.isinf(number):
        return "inf", number
    return "number", number


def _require_digit(digits):
    if isinstance(digits, bool):
        raise ValueError("bool is not numeric")
    if not isinstance(digits, (int, float)) or (
        isinstance(digits, float) and math.isnan(digits)
    ):
        raise ValueError("digits must be numeric")


def _require_range(sci_range):
    if isinstance(sci_range, bool) or not isinstance(sci_range, (int, float)):
        raise ValueError("sci_range must be numeric")
    if isinstance(sci_range, float) and math.isnan(sci_range):
        raise ValueError("sci_range must be numeric")


def _require_separator(sci_sep):
    if not isinstance(sci_sep, str):
        raise ValueError("sci_sep must be a string")
