"""Format milliseconds, seconds, and difftime values as short strings."""

import math

from prettyunits._difftime import Difftime
from prettyunits._r import r_mod, r_round

_MS_DAY = 86_400_000
_MS_HOUR = 3_600_000
_MS_MINUTE = 60_000
_UNITS = ("d", "h", "m", "s")


def pretty_ms(ms, compact=False):
    """Format milliseconds. A number returns a string or None; a list returns a list."""
    values, scalar = _as_numeric(ms, "ms")
    if not values:
        return []
    formatted = [_format_ms(value, compact) for value in values]
    if scalar:
        return formatted[0]
    return formatted


def pretty_sec(sec, compact=False):
    """Format seconds by converting them to milliseconds."""
    values, scalar = _as_numeric(sec, "sec")
    milliseconds = [None if value is None else value * 1000 for value in values]
    if scalar:
        return pretty_ms(milliseconds[0], compact=compact)
    return pretty_ms(milliseconds, compact=compact)


def pretty_dt(dt, compact=False):
    """Format a difftime through its length in seconds."""
    if not isinstance(dt, Difftime):
        raise ValueError("dt must be a difftime")
    seconds = dt.seconds
    if len(seconds) == 1:
        return pretty_sec(seconds[0], compact=compact)
    return pretty_sec(list(seconds), compact=compact)


def _as_numeric(value, label):
    if isinstance(value, list):
        for item in value:
            _require_numeric(item, label)
        return value, False
    _require_numeric(value, label)
    return [value], True


def _require_numeric(value, label):
    if isinstance(value, bool) or not (value is None or isinstance(value, (int, float))):
        raise ValueError(f"{label} must be numeric")


def _format_ms(ms, compact):
    pieces = _parse(ms)
    if compact:
        return _compact(pieces)
    # The approximate form is built even when the millisecond form is selected.
    approximate = _merge(pieces)
    if _missing(ms) or ms < 1000:
        return _milliseconds(ms)
    return approximate


def _parse(ms):
    if _missing(ms):
        return (None, None, None, None)
    return (
        _floor(ms / _MS_DAY),
        _floor(r_mod(ms / _MS_HOUR, 24)),
        _floor(r_mod(ms / _MS_MINUTE, 60)),
        r_round(r_mod(ms / 1000, 60), 1),
    )


def _floor(value):
    if math.isnan(value) or math.isinf(value):
        return value
    return math.floor(value)


def _milliseconds(ms):
    if _missing(ms):
        return None
    return f"{_as_character(math.ceil(ms))}ms"


def _merge(pieces):
    if all(_missing(piece) for piece in pieces):
        return None
    parts = []
    for piece, unit in zip(pieces, _UNITS):
        # if(NaN) is an error. Inf reaches this because Inf modulo 24 is NaN.
        if _missing(piece):
            raise ValueError("argument is not interpretable as logical")
        if piece:
            parts.append(f"{_as_character(piece)}{unit} ")
    return "".join(parts).strip()


def _compact(pieces):
    chosen = _first_positive(pieces)
    if chosen is None:
        return None
    return "~" + _as_character(pieces[chosen]) + _UNITS[chosen]


def _first_positive(pieces):
    for index, piece in enumerate(pieces):
        if _missing(piece):
            continue
        if piece > 0:
            return index
    return None


def _missing(value):
    if value is None:
        return True
    return isinstance(value, float) and math.isnan(value)


def _as_character(value):
    """R paste0 uses as.character, which prints 55 as 55 and 1.4 as 1.4.

    The significant digits come from 15 digits. Scientific notation is used
    when it is no longer than fixed notation, with a signed two-digit exponent.
    Fixed notation is printed from the double itself, so 7460144771039909 keeps
    all 16 digits.
    """
    if isinstance(value, bool) or value is None:
        raise ValueError("ms must be numeric")
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    sign = "-" if value < 0 else ""
    mantissa, exponent_text = format(abs(value), ".14e").split("e")
    exponent = int(exponent_text)
    digits = mantissa.replace(".", "").rstrip("0") or "0"
    scientific = digits[0] + ("." + digits[1:] if len(digits) > 1 else "")
    scientific = f"{sign}{scientific}e{exponent:+03d}"
    decimals = max(0, len(digits) - exponent - 1)
    fixed = f"{sign}{abs(value):.{decimals}f}"
    if len(fixed) <= len(scientific):
        return fixed
    return scientific
