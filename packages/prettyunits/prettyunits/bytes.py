"""Byte amounts and human-readable byte strings from prettyunits."""

import math
import re

from prettyunits._r import (
    format_fixed,
    format_numeric,
    justify_right,
    match_arg,
    na_subscript_positions,
    r_as_integer,
)

_UNITS0 = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
_STYLES = ["default", "nopad", "6"]
_LEADING_SPACE = re.compile(r"^\s+")


class ComputedBytes:
    """One amount, unit, and sign flag for each input byte count."""

    def __init__(self, amount, unit, negative):
        self.amount = amount
        self.unit = unit
        self.negative = negative


def _r_colon(start, end):
    """R's `start:end`, counting down when `start` is past `end`."""
    if start <= end:
        return list(range(start, end + 1))
    return list(range(start, end - 1, -1))


def _at(values, index):
    """1-based lookup. An index outside the vector is NA."""
    if index < 1 or index > len(values):
        return None
    return values[index - 1]


def _is_missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _is_nan(value):
    return isinstance(value, float) and math.isnan(value)


def _r_less(left, right):
    """R `<`. NA and NaN compare as missing."""
    if _is_missing(left) or _is_missing(right):
        return None
    return left < right


def _as_numeric(bytes):
    """R `is.numeric` vector. None is NA and float nan is NaN."""
    if isinstance(bytes, bool) or isinstance(bytes, str):
        raise ValueError("is.numeric(bytes) is not TRUE")
    if bytes is None or isinstance(bytes, (int, float)):
        items = [bytes]
    elif isinstance(bytes, (list, tuple)):
        items = list(bytes)
    else:
        raise ValueError("is.numeric(bytes) is not TRUE")

    values = []
    for item in items:
        if isinstance(item, bool) or isinstance(item, str) or not (
            item is None or isinstance(item, (int, float))
        ):
            raise ValueError("is.numeric(bytes) is not TRUE")
        if item is None:
            values.append(None)
        else:
            value = float(item)
            values.append(float("nan") if math.isnan(value) else value)
    return values


def _base_limits():
    """`c(1000, 999950 * 1000 ^ (seq_len(length(units0) - 2) - 1))`."""
    steps = range(1, len(_UNITS0) - 2 + 1)
    tail = [999950.0 * (1000.0 ** (step - 1)) for step in steps]
    return [1000.0, *tail]


def _column_true_counts(values, limits):
    """`colSums` of the column-major matrix `value < limit`."""
    counts = []
    for value in values:
        total = 0.0
        saw_missing = False
        for limit in limits:
            flag = _r_less(value, limit)
            if flag is None:
                saw_missing = True
            elif flag:
                total += 1.0
        counts.append(None if saw_missing else total)
    return counts


def _scale(value, exponent):
    """`value / 1000 ^ exponent`. A missing exponent makes the quotient missing."""
    if exponent is None or value is None:
        return None
    if math.isnan(value):
        return float("nan")
    return value / (1000.0 ** float(exponent))


def compute_bytes(bytes, smallest_unit="B"):
    """Split each byte count into an amount, a unit, and a sign flag."""
    values = _as_numeric(bytes)
    if isinstance(smallest_unit, (list, tuple)):
        if len(smallest_unit) != 1:
            raise ValueError("length(smallest_unit) == 1 is not TRUE")
        smallest_unit = smallest_unit[0]
    if smallest_unit is None or not isinstance(smallest_unit, str):
        raise ValueError("is.character(smallest_unit) is not TRUE")
    if smallest_unit not in _UNITS0:
        raise ValueError("smallest_unit %in% units0 is not TRUE")

    limits0 = _base_limits()
    low = _UNITS0.index(smallest_unit) + 1
    units = [_at(_UNITS0, index) for index in _r_colon(low, len(_UNITS0))]
    limits = [_at(limits0, index) for index in _r_colon(low, len(limits0))]

    negative = [not _is_missing(value) and value < 0 for value in values]
    absolute = []
    for value in values:
        if value is None:
            absolute.append(None)
        elif math.isnan(value):
            absolute.append(float("nan"))
        else:
            absolute.append(abs(value))

    counts = _column_true_counts(absolute, limits)
    n_limits = len(limits)
    exponents = []
    for count in counts:
        if count is None:
            exponents.append(None)
        else:
            exponents.append(n_limits - count + low - 1)

    amount = [_scale(value, exponent) for value, exponent in zip(absolute, exponents)]
    unit = []
    for exponent in exponents:
        if exponent is None:
            unit.append(None)
        else:
            unit.append(_at(units, math.trunc(exponent - low + 2)))

    for index, value in enumerate(absolute):
        if not _is_missing(value) and value == 0.0:
            amount[index] = 0.0
            unit[index] = units[0]

    for index, value in enumerate(absolute):
        if _is_missing(value):
            amount[index] = None
            unit[index] = _UNITS0[low - 1]
    for index, value in enumerate(absolute):
        if _is_nan(value):
            amount[index] = float("nan")

    return ComputedBytes(amount, unit, negative)


def _integer_amount(amount):
    """R `is.na(amount) | amount == as.integer(amount)`: True, False, or None (NA).

    `as.integer` of Inf is NA, so an infinite amount gives NA here.
    """
    if _is_missing(amount):
        return True
    converted = r_as_integer(amount)
    if converted is None:
        return None
    return amount == converted


def _signed(amount, negative):
    if amount is None:
        return None
    if math.isnan(amount):
        return float("nan")
    return (-1.0 if negative else 1.0) * amount


def _pretty_default(values):
    sizes = compute_bytes(values)
    amount = sizes.amount
    result = [""] * len(amount)
    integer_at, fraction_at = na_subscript_positions([_integer_amount(v) for v in amount])
    signed = [_signed(amount[index], sizes.negative[index]) for index in integer_at]
    for index, text in zip(integer_at, format_numeric(signed)):
        result[index] = text
    for index in fraction_at:
        result[index] = format_fixed(_signed(amount[index], sizes.negative[index]), 2)
    pasted = [f"{result[index]} {sizes.unit[index]}" for index in range(len(amount))]
    return justify_right(pasted)


def _pretty_nopad(values):
    return [_LEADING_SPACE.sub("", text) for text in _pretty_default(values)]


def _pretty_6(values):
    sizes = compute_bytes(values, smallest_unit="kB")
    amount = sizes.amount
    unit = list(sizes.unit)
    missing = [_is_missing(value) for value in amount]
    nan = [_is_nan(value) for value in amount]
    negative = [
        not missing[index] and not nan[index] and sizes.negative[index]
        for index in range(len(amount))
    ]
    below_10 = []
    below_100 = []
    at_least_100 = []
    for index, value in enumerate(amount):
        eligible = not missing[index] and not nan[index] and not negative[index]
        below_10.append(eligible and value < 10)
        below_100.append(eligible and value >= 10 and value < 100)
        at_least_100.append(eligible and value >= 100)

    for index, flag in enumerate(negative):
        if flag:
            unit[index] = "kB"

    formatted = [""] * len(amount)
    for index, flag in enumerate(missing):
        if flag:
            formatted[index] = " NA"
    for index, flag in enumerate(nan):
        if flag:
            formatted[index] = "NaN"
    for index, flag in enumerate(negative):
        if flag:
            formatted[index] = "< 0"
    for index, flag in enumerate(below_10):
        if flag:
            formatted[index] = f"{amount[index]:.1f}"
    for index, flag in enumerate(below_100):
        if flag:
            formatted[index] = f" {amount[index]:.0f}"
    for index, flag in enumerate(at_least_100):
        if flag:
            formatted[index] = format_fixed(amount[index], 0)
    return [f"{formatted[index]} {unit[index]}" for index in range(len(amount))]


def pretty_bytes(bytes, style=("default", "nopad", "6")):
    """Format byte counts in the default, nopad, or width-6 style."""
    scalar = not isinstance(bytes, (list, tuple))
    chosen = match_arg(style, _STYLES)
    values = _as_numeric(bytes)
    if chosen == "default":
        result = _pretty_default(values)
    elif chosen == "nopad":
        result = _pretty_nopad(values)
    else:
        result = _pretty_6(values)
    if not values:
        return []
    if scalar:
        return result[0]
    return result
