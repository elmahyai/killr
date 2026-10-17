"""Human-readable p-values."""

import math

from prettyunits.rounding import pretty_round

_MINVAL_TYPE = "is.numeric(minval) & !is.factor(minval) & !is.na(minval)"
_MINVAL_RANGE = "minval < 1 & minval > 0"
_X_TYPE = "is.numeric(x) & !is.factor(x)"
_X_RANGE = "is.na(x) | (x <= 1 & x >= 0)"


def pretty_p_value(x, minval=0.0001):
    """Format p-values, hiding those below ``minval``.

    A missing p-value stays ``None``, not the string ``"NA"``. If every
    value is missing, ``x`` does not have to be numeric.
    """
    _require_minval(minval)
    values, scalar = _as_values(x)
    if all(_is_missing(value) for value in values):
        out = [None] * len(values)
        return out[0] if scalar else out
    if not all(_is_numeric(value) or _is_missing(value) for value in values):
        _stop(_X_TYPE)
    if not all(_in_unit_or_missing(value) for value in values):
        _stop(_X_RANGE)
    ndigits = -math.floor(math.log10(float(minval)))
    below = "<" + pretty_round(float(minval), digits=ndigits)
    out = [None] * len(values)
    over_at = []
    over = []
    for index, value in enumerate(values):
        if _is_missing(value):
            continue
        number = float(value)
        if number < minval:
            out[index] = below
        else:
            over_at.append(index)
            over.append(number)
    if over:
        printed = pretty_round(over, digits=ndigits)
        for index, text in zip(over_at, printed):
            out[index] = text
    if scalar:
        return out[0]
    return out


def _require_minval(minval):
    if (
        isinstance(minval, bool)
        or not isinstance(minval, (int, float))
        or (isinstance(minval, float) and math.isnan(minval))
    ):
        _stop(_MINVAL_TYPE)
    if not (minval < 1 and minval > 0):
        _stop(_MINVAL_RANGE)


def _stop(condition):
    raise ValueError(f"{condition} is not TRUE")


def _as_values(x):
    if isinstance(x, (list, tuple)):
        return list(x), False
    return [x], True


def _is_missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _is_numeric(value):
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _in_unit_or_missing(value):
    if _is_missing(value):
        return True
    number = float(value)
    return 0.0 <= number <= 1.0
