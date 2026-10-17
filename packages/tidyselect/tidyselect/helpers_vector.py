"""Selection helpers from tidyselect 1.2.1.

``all_of`` returns 1-based positions of names in the selection context.
``any_of`` returns those positions for names that exist and drops the rest.
``vars`` is that context. ``None`` is the out-of-context call. ``all_of``
warns and returns ``x``. ``any_of`` errors.
"""

from __future__ import annotations

import math
import warnings

from tidyselect.helpers_misc import TidyselectError, _friendly, _peek

_R_INT_MAX = 2147483647
_OUTSIDE = (
    "Using `all_of()` outside of a selecting function was deprecated in tidyselect\n"
    "1.2.0.\n"
    "\u2139 See details at\n"
    "  <https://tidyselect.r-lib.org/reference/faq-selection-context.html>"
)
_DOTS = (
    "`...` must be empty.\n"
    "\u2139 Did you forget `c()`?\n"
    '\u2139 The expected syntax is `any_of(c("a", "b"))`, not `any_of("a", "b")`'
)


def all_of(x, vars=None):
    """Return the positions of each name in ``x``.

    ``vars`` is the character vector of names in the selection context.
    When it is omitted, the call is outside that context: R warns and
    returns ``x``. A name that is not in ``vars`` is an error. Numeric
    positions are returned as integers, including positions past the end.
    """
    if vars is None:
        warnings.warn(_OUTSIDE, UserWarning, stacklevel=2)
        return x
    index = _name_index(_character_vars(vars))
    kind, values = _as_subscript(x)
    if kind == "empty":
        return []
    if kind == "character":
        return _locations(values, index)
    return _cast_integers(values)


def any_of(x, *extra, vars=None, **unknown):
    """Return positions for the names in ``x`` that exist in ``vars``.

    Missing names are dropped, and a repeated name is kept once, in the
    order of ``x``. A numeric position past the end of ``vars`` is dropped.
    ``vars`` is keyword-only. Extra arguments are the empty-dots error.
    When ``vars`` is omitted, the call is outside a selection context.
    """
    if vars is None:
        _peek("any_of")
    if extra or unknown:
        raise TidyselectError(_DOTS)
    names = _character_vars(vars)
    index = _name_index(names)
    kind, values = _as_subscript(x)
    if kind == "empty":
        return []
    if kind == "character":
        return _locations(_intersect_present(values, names), index)
    return _within_length(_cast_integers(values), len(names))


def _character_vars(vars):
    if isinstance(vars, str):
        return [vars]
    if isinstance(vars, (list, tuple)):
        out = []
        for item in vars:
            if isinstance(item, str) or item is None:
                out.append(item)
            else:
                raise TidyselectError("`vars` must be a character vector")
        return out
    raise TidyselectError("`vars` must be a character vector")


def _name_index(vars):
    index = {}
    for position, name in enumerate(vars, start=1):
        if isinstance(name, str) and name not in index:
            index[name] = position
    return index


def _as_subscript(x):
    if x is None:
        return "empty", []
    if isinstance(x, str):
        return "character", [x]
    if isinstance(x, bool):
        _reject_logical([x])
    if isinstance(x, int):
        return "number", [x]
    if isinstance(x, float):
        return "number", [x]
    if isinstance(x, complex):
        _reject(_complex_phrase(x))
    if isinstance(x, (bytes, bytearray)):
        _reject(_raw_phrase(x))
    if isinstance(x, (list, tuple)):
        return _as_subscript_vector(list(x))
    if callable(x):
        _reject("a function")
    _reject(_friendly(x))


def _as_subscript_vector(values):
    if not values:
        return "empty", []
    if all(item is None for item in values):
        return "number", values
    if any(isinstance(item, bool) for item in values):
        _reject_logical(values)
    if any(isinstance(item, complex) for item in values):
        if len(values) == 1:
            _reject(_complex_phrase(values[0]))
        _reject("a complex vector")
    if any(isinstance(item, (bytes, bytearray)) for item in values):
        if len(values) == 1:
            _reject(_raw_phrase(values[0]))
        _reject("a raw vector")
    if any(isinstance(item, str) for item in values):
        if any(not isinstance(item, str) and item is not None for item in values):
            _reject("a list")
        return "character", values
    if all(item is None or isinstance(item, (int, float)) for item in values):
        return "number", values
    _reject("a list")


def _intersect_present(values, names):
    """Keep the first copy of each name that is in ``names``, plus one ``NA``."""
    allowed = {name for name in names if isinstance(name, str)}
    seen = set()
    out = []
    for value in values:
        if value is not None and value not in allowed:
            continue
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _within_length(values, limit):
    """Keep ``NA`` and positions ``<= limit``. Drop positions past the end."""
    out = []
    for value in values:
        if value is None or value <= limit:
            out.append(value)
    return out


def _locations(values, index):
    empties = [position for position, value in enumerate(values, start=1) if value == ""]
    if empties:
        raise TidyselectError(_empty_message(empties))
    out = []
    missing = []
    has_na = False
    for value in values:
        if value is None:
            out.append(None)
            has_na = True
            continue
        found = index.get(value)
        if found is None:
            missing.append(value)
        else:
            out.append(found)
    if missing:
        raise TidyselectError(_missing_message(missing, has_na))
    return out


def _cast_integers(values):
    out = []
    for value in values:
        out.append(_one_integer(value))
    return out


def _one_integer(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _precision_error()
    if isinstance(value, float):
        if math.isinf(value) or abs(value) > _R_INT_MAX or value != math.trunc(value):
            raise _precision_error()
        return int(value)
    if value > _R_INT_MAX or value < -_R_INT_MAX:
        raise _precision_error()
    return value


def _precision_error():
    raise TidyselectError(
        "Can't subset elements.\n"
        "\u2716 Can't convert from <double> to <integer> due to loss of precision."
    )


def _reject(shown):
    raise TidyselectError(
        "Can't subset elements.\n"
        f"\u2716 Subscript must be numeric or character, not {shown}."
    )


def _reject_logical(values):
    if len(values) == 1 and values[0] is True:
        _reject("`TRUE`")
    if len(values) == 1 and values[0] is False:
        _reject("`FALSE`")
    _reject("a logical vector")


def _missing_message(missing, has_na):
    if has_na:
        detail = "Elements NA don't exist."
    else:
        detail = _limited_sentence(
            [_tick(name) for name in missing],
            one="Element {body} doesn't exist.",
            many="Elements {body} don't exist.",
        )
    return "Can't subset elements that don't exist.\n\u2716 " + detail


def _empty_message(locations):
    detail = _limited_sentence(
        [str(location) for location in locations],
        one="It has an empty string at location {body}.",
        many="It has an empty string at locations {body}.",
    )
    return (
        "Can't subset elements.\n"
        "\u2716 Subscript can't contain the empty string.\n"
        "\u2716 " + detail
    )


def _limited_sentence(parts, one, many):
    count = len(parts)
    if count > 5:
        body = ", ".join(parts[:5]) + ", etc."
    elif count == 1:
        body = parts[0]
    elif count == 2:
        body = f"{parts[0]} and {parts[1]}"
    else:
        body = ", ".join(parts[:-1]) + ", and " + parts[-1]
    template = one if count == 1 else many
    sentence = template.format(body=body)
    if sentence.endswith("etc.."):
        return sentence[:-1]
    return sentence


def _tick(name):
    return "`" + name.replace("`", "\\`") + "`"


def _complex_phrase(value):
    real = float(value.real)
    imag = float(value.imag)
    sign = "+" if math.copysign(1.0, imag) > 0 else "-"
    return f"the complex number {_plain_number(real)}{sign}{_plain_number(abs(imag))}i"


def _plain_number(value):
    if value == math.trunc(value) and abs(value) <= _R_INT_MAX:
        return str(int(value))
    return str(value)


def _raw_phrase(value):
    if len(value) == 0:
        return "an empty raw vector"
    if len(value) == 1:
        return f"the raw value {value[0]:02x}"
    return "a raw vector"
