"""Linear quantities: an amount, an SI prefix, and a sign."""

import math
import re

from prettyunits._r import (
    DOUBLE_EPS,
    format_fixed,
    format_numeric,
    justify_right,
    match_arg,
    na_subscript_positions,
    r_as_integer,
    r_round,
)

_NOT_NUMERIC = "is.numeric(number) is not TRUE"
_PREFIXES0 = [
    "y", "z", "a", "f", "p", "n", "u", "m", "",
    "k", "M", "G", "T", "P", "E", "Z", "Y",
]
_ZEROSHIF0 = 9
# 999950 * 1000 ^ (seq_len(n) - (zeroshif0 + 1)). Float powers, as in R.
_LIMITS0 = [
    999950.0 * (1000.0 ** (i - (_ZEROSHIF0 + 1)))
    for i in range(1, len(_PREFIXES0) + 1)
]
_STYLES = ["default", "nopad", "6"]


class _Quantity:
    """`amount`, `prefix`, and `negative` are lists, including for one number."""

    def __init__(self, amount, prefix, negative):
        self.amount = amount
        self.prefix = prefix
        self.negative = negative


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _nan(value):
    return isinstance(value, float) and math.isnan(value)


def _is_scalar(number):
    return number is None or (
        isinstance(number, (int, float)) and not isinstance(number, bool)
    )


def _coerce(item):
    if isinstance(item, bool) or isinstance(item, str):
        raise ValueError(_NOT_NUMERIC)
    if item is None:
        return None
    if isinstance(item, float):
        return item
    if isinstance(item, int):
        return float(item)
    raise ValueError(_NOT_NUMERIC)


def _as_vector(number):
    if isinstance(number, bool) or isinstance(number, str):
        raise ValueError(_NOT_NUMERIC)
    if _is_scalar(number):
        return [_coerce(number)]
    if isinstance(number, (list, tuple)):
        return [_coerce(item) for item in number]
    raise ValueError(_NOT_NUMERIC)


def _smallest_prefix(value):
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError("length(smallest_prefix) == 1 is not TRUE")
        value = value[0]
    if not isinstance(value, str):
        raise ValueError("is.character(smallest_prefix) is not TRUE")
    if value not in _PREFIXES0:
        raise ValueError("smallest_prefix %in% prefixes0 is not TRUE")
    return value


def _raw_exponent(value, limits, nrow, zeroshift):
    """`nrow - colSums(mat < limits) - (zeroshift - 1)`. NA comparisons sum to NA."""
    if _missing(value):
        return None
    below = 0
    for limit in limits:
        if value < limit:
            below += 1
    return nrow - below - (zeroshift - 1)


def _in_range(exponent, nrow, zeroshift):
    """`max(min(exponent, nrow - zeroshift), 1 - zeroshift)`.

    `min(..., na.rm = FALSE)` stays missing, and `max(NA, lower, na.rm = TRUE)`
    is the lower bound.
    """
    upper = nrow - zeroshift
    lower = 1 - zeroshift
    if exponent is None:
        clipped = None
    else:
        clipped = min(exponent, upper)
    if clipped is None:
        return lower
    return max(clipped, lower)


def _prefixes_at(prefixes, index):
    """R `prefixes[index]` for one index. Zero is empty. A negative index drops."""
    if index > 0:
        return [prefixes[index - 1]]
    if index == 0:
        return []
    drop = -index
    if 1 <= drop <= len(prefixes):
        return [prefixes[i] for i in range(len(prefixes)) if i + 1 != drop]
    return list(prefixes)


def compute_num(number, smallest_prefix="y"):
    """Split each number into an amount, a prefix, and a negative flag."""
    values = _as_vector(number)
    smallest_prefix = _smallest_prefix(smallest_prefix)
    low = _PREFIXES0.index(smallest_prefix) + 1
    zeroshift = _ZEROSHIF0 + 1 - low
    prefixes = _PREFIXES0[low - 1 :]
    limits = _LIMITS0[low - 1 :]
    nrow = len(_PREFIXES0) - low + 1

    negative = [False if _missing(value) else value < 0 for value in values]
    absolute = [value if _missing(value) else abs(value) for value in values]
    raw = [_raw_exponent(value, limits, nrow, zeroshift) for value in absolute]
    # sapply walks each exponent. An empty input skips that step.
    if raw:
        exponents = [_in_range(item, nrow, zeroshift) for item in raw]
    else:
        exponents = []

    amount = []
    prefix = []
    for value, exponent in zip(absolute, exponents):
        if value is None:
            scaled = None
        elif _nan(value):
            scaled = float("nan")
        else:
            scaled = value / (1000.0 ** exponent)
        amount.append(scaled)
        prefix.append(prefixes[exponent + zeroshift - 1])

    zeros = []
    compared_missing = False
    for i, value in enumerate(absolute):
        if _missing(value):
            compared_missing = True
        elif value == 0.0:
            zeros.append(i)
    if zeros:
        replacement = _prefixes_at(prefixes, zeroshift)
        if not replacement:
            raise ValueError("replacement has length zero")
        if compared_missing and len(replacement) != 1:
            raise ValueError("NAs are not allowed in subscripted assignments")
        for n, i in enumerate(zeros):
            amount[i] = 0.0
            prefix[i] = replacement[n % len(replacement)]

    for i, value in enumerate(absolute):
        if _missing(value):
            amount[i] = None
            prefix[i] = ""
    for i, value in enumerate(absolute):
        if _nan(value):
            amount[i] = float("nan")

    return _Quantity(amount, prefix, negative)


def _signed(amount, negative):
    if _missing(amount):
        return amount
    if negative:
        return -amount
    return amount


def _counts_as_integer(amount):
    """R `is.na(amount) | abs(amount - as.integer(amount)) <= eps`: True, False, or None (NA).

    `as.integer` of Inf is NA, so an infinite amount gives NA here.
    """
    if _missing(amount):
        return True
    truncated = r_as_integer(amount)
    if truncated is None:
        return None
    return abs(amount - truncated) <= DOUBLE_EPS


def _pretty_num_default(number):
    parts = compute_num(number)
    texts = [""] * len(parts.amount)
    integer_at, fraction_at = na_subscript_positions(
        [_counts_as_integer(amount) for amount in parts.amount]
    )
    signed_integers = [_signed(parts.amount[i], parts.negative[i]) for i in integer_at]
    for i, text in zip(integer_at, format_numeric(signed_integers)):
        texts[i] = text
    for i in fraction_at:
        texts[i] = format_fixed(_signed(parts.amount[i], parts.negative[i]), 2)
    pasted = [f"{texts[i]} {parts.prefix[i]}" for i in range(len(texts))]
    return justify_right(pasted)


def _pretty_num_nopad(number):
    return [re.sub(r"^\s+", "", text) for text in _pretty_num_default(number)]


def _pretty_num_6(number):
    parts = compute_num(number, smallest_prefix="y")
    amounts = [r_round(amount, 2) for amount in parts.amount]
    famt = []
    for amount, negative in zip(amounts, parts.negative):
        missing = _missing(amount)
        nan = _nan(amount)
        neg = (not missing) and negative
        if nan:
            famt.append(" NaN")
        elif missing:
            famt.append("  NA")
        elif not neg and amount < 10:
            famt.append(f"{amount:.2f}")
        elif not neg and amount < 100:
            famt.append(f"{amount:.1f}")
        elif not neg:
            famt.append(" " + format_fixed(amount, 0))
        elif amount < 10:
            famt.append(f"-{amount:.1f}")
        elif amount < 100:
            famt.append(" -" + format_fixed(amount, 0))
        else:
            famt.append("-" + format_fixed(amount, 0))
    out = []
    for text, prefix in zip(famt, parts.prefix):
        # A trailing space is the empty prefix. Replace that one space with two.
        out.append(re.sub(r" $", "  ", f"{text} {prefix}"))
    return out


def pretty_num(number, style=("default", "nopad", "6")):
    """Format linear quantities. One number returns a string. A list returns a list."""
    chosen = match_arg(style, _STYLES)
    scalar = _is_scalar(number)
    if chosen == "6":
        result = _pretty_num_6(number)
    elif chosen == "nopad":
        result = _pretty_num_nopad(number)
    else:
        result = _pretty_num_default(number)
    if scalar:
        return result[0]
    return result
