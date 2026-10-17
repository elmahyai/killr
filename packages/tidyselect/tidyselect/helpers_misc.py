"""Selection helpers from tidyselect 1.2.1.

``everything`` and ``last_col`` return 1-based positions. ``vars`` is the
character vector of names. ``None`` reads the selection context, which is
empty until a selecting function sets it.
"""

from __future__ import annotations

import math
import warnings

_R_INT_MAX = 2147483647
_MANTISSA = 2**52
_CONTEXT = (
    "`{name}()` must be used within a *selecting* function.\n"
    "\u2139 See <https://tidyselect.r-lib.org/reference/faq-selection-context.html> for\n"
    "  details."
)


class TidyselectError(Exception):
    """An error raised by these selection helpers."""


def everything(vars=None):
    """Return every variable position, from 1 through the length of ``vars``."""
    if vars is None:
        vars = _peek("everything")
    return list(range(1, _var_count(vars) + 1))


def last_col(offset=0, vars=None):
    """Return the variable position ``offset`` places before the end."""
    if not _is_integerish(offset, n=1):
        raise TidyselectError(
            f"`offset` must be a single integer, not {_friendly(offset)}."
        )
    if vars is None:
        vars = _peek("last_col")
    count = _var_count(vars)
    value = _number(offset)
    if _truth(value) and count <= value:
        shown = _format_offset(value)
        raise TidyselectError(
            f"`offset` ({shown}) must be smaller than the number of columns ({count})."
        )
    if count == 0:
        raise TidyselectError("Can't select last column when input is empty.")
    return _r_sub(count, _r_as_integer(value))


def _peek(name):
    raise TidyselectError(_CONTEXT.format(name=name))


def _var_count(vars):
    if isinstance(vars, (str, bool, int, float, complex)):
        return 1
    return len(vars)


def _is_integerish(value, n=None):
    kind, values = _classify(value)
    if kind not in ("integer", "double"):
        return False
    if n is not None and len(values) != n:
        return False
    if kind == "integer":
        return True
    return all(_double_integerish(item) for item in values)


def _double_integerish(value):
    if isinstance(value, int):
        return abs(value) <= _MANTISSA
    if math.isnan(value) or math.isinf(value):
        return True
    if abs(value) > _MANTISSA:
        return False
    return value == math.trunc(value)


def _number(value):
    _kind, values = _classify(value)
    return values[0]


def _truth(value):
    if isinstance(value, float) and math.isnan(value):
        raise TidyselectError("missing value where TRUE/FALSE needed")
    return value != 0


def _r_as_integer(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        if math.isinf(value):
            warnings.warn(
                "NAs introduced by coercion to integer range",
                RuntimeWarning,
                stacklevel=2,
            )
        return None
    if isinstance(value, float):
        value = int(value)
    if value > _R_INT_MAX or value < -_R_INT_MAX:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    return value


def _r_sub(count, offset):
    if offset is None:
        return None
    if count > _R_INT_MAX:
        return count - offset
    diff = count - offset
    if diff > _R_INT_MAX or diff < -_R_INT_MAX:
        warnings.warn(
            "NAs produced by integer overflow",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    return diff


def _format_offset(value):
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if isinstance(value, float) and math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    if isinstance(value, float) and abs(value) <= _MANTISSA and value == math.trunc(value):
        value = int(value)
    if isinstance(value, int):
        if -_R_INT_MAX <= value <= _R_INT_MAX:
            return str(value)
        return _format_exact_integer(value)
    return _as_character_double(value)


def _format_exact_integer(value):
    """R's ``as.character`` for an integer-valued double, from its exact digits."""
    if value == 0:
        return "0"
    negative = value < 0
    digits = str(abs(value))
    exponent = len(digits) - 1
    rest = digits[1:].rstrip("0")
    mantissa = digits[0] if rest == "" else f"{digits[0]}.{rest}"
    scientific = f"{mantissa}e{exponent:+03d}"
    if negative:
        scientific = "-" + scientific
        digits = "-" + digits
    if len(scientific) < len(digits):
        return scientific
    return digits


def _as_character_double(value):
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0.0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def _friendly(value):
    kind, values = _classify(value)
    size = len(values)
    if kind == "null":
        return "NULL"
    if kind == "logical":
        if size == 0:
            return "an empty logical vector"
        if size == 1:
            return "`TRUE`" if values[0] else "`FALSE`"
        return "a logical vector"
    if kind == "integer":
        if size == 0:
            return "an empty integer vector"
        if size == 1:
            return "an integer"
        return "an integer vector"
    if kind == "double":
        if size == 0:
            return "an empty numeric vector"
        if size == 1:
            return "a number"
        return "a double vector"
    if kind == "complex":
        if size == 0:
            return "an empty complex vector"
        if size == 1:
            return "a complex number"
        return "a complex vector"
    if kind == "character":
        if size == 0:
            return "an empty character vector"
        if size == 1:
            if values[0] == "":
                return '`""`'
            return "a string"
        return "a character vector"
    if kind == "raw":
        if size == 0:
            return "an empty raw vector"
        if size == 1:
            return "a raw value"
        return "a raw vector"
    if kind == "symbol":
        return "a symbol"
    if kind == "function":
        return "a function"
    if kind == "environment":
        return "an environment"
    if kind == "list":
        if size == 0:
            return "an empty list"
        return "a list"
    return "a list"


def _classify(value):
    if value is None:
        return "null", []
    if isinstance(value, bool):
        return "logical", [value]
    if isinstance(value, int):
        return _int_kind(value), [value]
    if isinstance(value, float):
        return "double", [value]
    if isinstance(value, complex):
        return "complex", [value]
    if isinstance(value, str):
        return "character", [value]
    if isinstance(value, (bytes, bytearray)):
        return "raw", list(value)
    if isinstance(value, (list, tuple)):
        return _classify_vector(value)
    if callable(value):
        return "function", [value]
    return "list", [value]


def _int_kind(value):
    if -_R_INT_MAX <= value <= _R_INT_MAX:
        return "integer"
    return "double"


def _classify_vector(value):
    if len(value) == 0:
        return "list", []
    if any(isinstance(item, (list, tuple, dict)) or item is None for item in value):
        return "list", list(value)
    kinds = []
    numbers = []
    for item in value:
        if isinstance(item, bool):
            kinds.append("logical")
            numbers.append(item)
        elif isinstance(item, int):
            kinds.append(_int_kind(item))
            numbers.append(item)
        elif isinstance(item, float):
            kinds.append("double")
            numbers.append(item)
        elif isinstance(item, complex):
            kinds.append("complex")
        elif isinstance(item, str):
            kinds.append("character")
        elif isinstance(item, (bytes, bytearray)):
            return "list", list(value)
        else:
            return "list", list(value)
    if "character" in kinds:
        return "character", [str(item) for item in value]
    if "complex" in kinds:
        return "complex", list(value)
    if "double" in kinds:
        return "double", numbers
    if "integer" in kinds:
        return "integer", numbers
    if "logical" in kinds:
        return "logical", numbers
    return "list", list(value)
