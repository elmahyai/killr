"""Join and duplicate strings the way stringi 1.8.9 does.

Missing characters are ``stringi._na.NA``. The string ``"NA"`` is a real
string. A Python ``int`` is formatted as an R integer. A ``float`` is
formatted as an R double. ``None`` is R's ``NULL`` when it is a whole
argument, and a missing element when it sits inside a vector.
"""

from __future__ import annotations

import math
import re
import warnings

from stringi._na import NA

_BYTE_LIMIT = 2147483647
_INT_MIN = -2147483647
_INT_MAX = 2147483647
_TRUE_WORDS = {"TRUE", "True", "true", "T"}
_FALSE_WORDS = {"FALSE", "False", "false", "F"}
_HEX = re.compile(r"[+-]?0[xX][0-9A-Fa-f]+$")
_NUMBER = re.compile(r"[+-]?(?:(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|Inf|NaN)$")
_TOO_LONG = "Elements of character vectors (CHARSXPs) are limited to 2^31-1 bytes"


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=3)


def _require_bytes(nbytes: int) -> None:
    if nbytes > _BYTE_LIMIT:
        raise ValueError(_TOO_LONG)


def _checked(text: str) -> str:
    # Four bytes is the longest UTF-8 encoding of one code point.
    if len(text) > _BYTE_LIMIT // 4:
        _require_bytes(len(text.encode("utf-8")))
    return text


def _r_character_double(value: float) -> str:
    """Match R's as.character for a finite double."""

    if value == 0.0:
        return "0"
    negative = value < 0
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


def _character_scalar(value: object) -> object:
    if value is NA or value is None:
        return NA
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        return _r_character_double(value)
    if isinstance(value, str):
        return value
    raise TypeError


def _prepare_string(value: object, argname: str) -> list:
    if value is None:
        return []
    if isinstance(value, range):
        value = list(value)
    if isinstance(value, (list, tuple)):
        try:
            return [_character_scalar(item) for item in value]
        except TypeError:
            raise ValueError(
                f"argument `{argname}` should be a character vector "
                "(or an object coercible to)"
            ) from None
    try:
        return [_character_scalar(value)]
    except TypeError:
        raise ValueError(
            f"argument `{argname}` should be a character vector "
            "(or an object coercible to)"
        ) from None


def _integer_token(token: str, flags: set[str]) -> object:
    if _HEX.fullmatch(token):
        number = int(token, 16)
    elif _NUMBER.fullmatch(token):
        numeric = float(token)
        if math.isnan(numeric):
            return NA
        if math.isinf(numeric):
            flags.add("range")
            return NA
        number = math.trunc(numeric)
    else:
        flags.add("coerce")
        return NA
    if number < _INT_MIN or number > _INT_MAX:
        flags.add("range")
        return NA
    return number


def _integer_scalar(value: object, flags: set[str]) -> object:
    if value is NA or value is None:
        return NA
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        if value < _INT_MIN or value > _INT_MAX:
            flags.add("range")
            return NA
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return NA
        if math.isinf(value):
            flags.add("range")
            return NA
        number = math.trunc(value)
        if number < _INT_MIN or number > _INT_MAX:
            flags.add("range")
            return NA
        return number
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return NA
        return _integer_token(stripped, flags)
    raise TypeError


def _prepare_integer(value: object, argname: str) -> list:
    flags: set[str] = set()
    if value is None:
        return []
    if isinstance(value, range):
        value = list(value)
    try:
        if isinstance(value, (list, tuple)):
            result = [_integer_scalar(item, flags) for item in value]
        else:
            result = [_integer_scalar(value, flags)]
    except TypeError:
        raise ValueError(
            f"argument `{argname}` should be an integer vector "
            "(or an object coercible to)"
        ) from None
    if "range" in flags:
        _warn("NAs introduced by coercion to integer range")
    if "coerce" in flags:
        _warn("NAs introduced by coercion")
    return result


def _logical_scalar(value: object) -> object:
    if value is NA or value is None:
        return NA
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float):
        if math.isnan(value):
            return NA
        return value != 0.0
    if isinstance(value, str):
        if value in _TRUE_WORDS:
            return True
        if value in _FALSE_WORDS:
            return False
        return NA
    raise TypeError


def _prepare_logical_1(value: object, argname: str, allow_na: bool) -> object:
    if value is None:
        raise ValueError(f"argument `{argname}` should be a non-empty vector")
    if isinstance(value, (list, tuple)):
        try:
            items = [_logical_scalar(item) for item in value]
        except TypeError:
            raise ValueError(
                f"argument `{argname}` should be a logical vector "
                "(or an object coercible to)"
            ) from None
    else:
        try:
            items = [_logical_scalar(value)]
        except TypeError:
            raise ValueError(
                f"argument `{argname}` should be a logical vector "
                "(or an object coercible to)"
            ) from None
    if len(items) == 0:
        raise ValueError(f"argument `{argname}` should be a non-empty vector")
    if len(items) > 1:
        _warn(
            f"argument `{argname}` should be a single logical value; "
            "only the first element is used"
        )
    chosen = items[0]
    if chosen is NA and not allow_na:
        raise ValueError(
            f"missing values in argument `{argname}` is not supported"
        )
    return chosen


def _prepare_string_1(value: object, argname: str) -> object:
    items = _prepare_string(value, argname)
    if len(items) == 0:
        raise ValueError(f"argument `{argname}` should be a non-empty vector")
    if len(items) > 1:
        _warn(
            f"argument `{argname}` should be a single character string; "
            "only the first element is used"
        )
    return items[0]


def _output_length(lengths: list[int]) -> int:
    if not lengths or any(n <= 0 for n in lengths):
        return 0
    longest = max(lengths)
    if any(longest % n != 0 for n in lengths):
        _warn("longer object length is not a multiple of shorter object length")
    return longest


def _flatten_no_sep(strings: list, na_empty: object) -> object:
    if na_empty is False and any(item is NA for item in strings):
        return NA
    parts = [item for item in strings if item is not NA]
    return _checked("".join(parts))


def _flatten_with_sep(strings: list, sep: str, na_empty: object, omit_empty: bool) -> object:
    if na_empty is False and any(item is NA for item in strings):
        return NA
    parts: list[str] = []
    started = False
    for item in strings:
        if na_empty is NA and item is NA:
            continue
        if omit_empty and (item is NA or item == ""):
            continue
        if started:
            parts.append(sep)
        else:
            started = True
        if item is not NA:
            parts.append(item)
    return _checked("".join(parts))


def stri_dup(str, times):
    """Duplicate each string and concatenate the copies.

    A missing string, a missing count, or a negative count yields a missing
    result. A count of zero yields an empty string. An empty input yields an
    empty vector.
    """

    strings = _prepare_string(str, "str")
    counts = _prepare_integer(times, "times")
    length = _output_length([len(strings), len(counts)])
    if length == 0:
        return []
    result = []
    string_count = len(strings)
    count_count = len(counts)
    for index in range(length):
        item = strings[index % string_count]
        count = counts[index % count_count]
        if item is NA or count is NA or count < 0:
            result.append(NA)
            continue
        if count == 0 or item == "":
            result.append("")
            continue
        _require_bytes(len(item.encode("utf-8")) * count)
        result.append(item * count)
    return result


def _join_rows(vectors: list[list], sep: str) -> list:
    height = max(len(vector) for vector in vectors)
    result = []
    for index in range(height):
        pieces = []
        missing = False
        for vector in vectors:
            item = vector[index % len(vector)]
            if item is NA:
                missing = True
                break
            pieces.append(item)
        if missing:
            result.append(NA)
        else:
            result.append(_checked(sep.join(pieces)))
    return result


def _join_nocollapse(vectors: list[list], sep) -> list:
    if not vectors or any(len(vector) == 0 for vector in vectors):
        return []
    # A missing sep is a vector of missing values and does not warn
    # about recycling. The length warning comes after sep is accepted.
    separator = _prepare_string_1(sep, "sep")
    if separator is NA:
        return [NA] * max(len(vector) for vector in vectors)
    _output_length([len(vector) for vector in vectors])
    return _join_rows(vectors, separator)


def _join_collapse(vectors: list[list], sep, collapse) -> list:
    # No arguments at all: one empty string, and sep is not inspected.
    if not vectors:
        return [""]
    if len(vectors) == 1:
        return stri_flatten(vectors[0], collapse)
    separator = _prepare_string_1(sep, "sep")
    between = _prepare_string_1(collapse, "collapse")
    if separator is NA or between is NA:
        return [NA]
    if any(len(vector) == 0 for vector in vectors):
        return [""]
    _output_length([len(vector) for vector in vectors])
    rows = _join_rows(vectors, separator)
    if any(item is NA for item in rows):
        return [NA]
    return [_checked(between.join(rows))]


def stri_join(*args, sep="", collapse=None, ignore_null=False):
    """Concatenate vectors element by element.

    ``stri_c`` and ``stri_paste`` are the same function. A missing element
    makes that result missing. A length-zero argument makes the result empty
    unless ``ignore_null`` drops it. ``collapse`` then joins the rows into
    one string. With one vector, ``sep`` is not inserted and ``collapse``
    is ``stri_flatten``.
    """

    ignore = _prepare_logical_1(ignore_null, "ignore_null", allow_na=False)
    vectors = []
    for arg in args:
        vector = _prepare_string(arg, "...")
        if ignore and len(vector) == 0:
            continue
        vectors.append(vector)
    if collapse is None:
        return _join_nocollapse(vectors, sep)
    return _join_collapse(vectors, sep, collapse)


def stri_flatten(str, collapse="", na_empty=False, omit_empty=False):
    """Join one vector into a single string.

    ``na_empty=False`` makes any missing element a missing result.
    ``na_empty=True`` treats a missing element as an empty string.
    ``na_empty=NA`` drops missing elements. ``omit_empty`` drops empty
    strings, and also missing elements when they are not already an error.
    An empty ``collapse`` ignores ``omit_empty``.
    """

    separator = _prepare_string_1(collapse, "collapse")
    na_flag = _prepare_logical_1(na_empty, "na_empty", allow_na=True)
    omit = _prepare_logical_1(omit_empty, "omit_empty", allow_na=False)
    if separator is NA:
        return [NA]
    strings = _prepare_string(str, "str")
    if len(strings) == 0:
        return [""]
    # The C++ empty-separator path never reads omit_empty.
    if separator == "":
        return [_flatten_no_sep(strings, na_flag)]
    return [_flatten_with_sep(strings, separator, na_flag, bool(omit))]


def _prepare_list(value: object) -> list[list]:
    if value is None or isinstance(value, (str, bytes, range)) or not isinstance(value, (list, tuple)):
        raise ValueError(
            "argument `x` should be a list of character vectors "
            "(or an object coercible to)"
        )
    vectors = []
    for item in value:
        vector = _prepare_string(item, "x")
        if len(vector) > 0:
            vectors.append(vector)
    return vectors


def stri_join_list(x, sep="", collapse=None):
    """Concatenate the strings in each vector of a list.

    ``stri_c_list`` and ``stri_paste_list`` are the same function. A
    length-zero vector, including ``None``, is dropped. Each remaining
    vector is flattened with ``sep``. ``collapse`` then joins those
    results. A missing element inside a vector makes that result missing.
    """

    vectors = _prepare_list(x)
    if not vectors:
        return []
    separator = _prepare_string_1(sep, "sep")
    rows = []
    for vector in vectors:
        # flatten's collapse is this function's sep. Defaults keep NA.
        flattened = stri_flatten(vector, separator)
        rows.append(flattened[0])
    if collapse is None:
        return rows
    return stri_flatten(rows, collapse)


stri_c = stri_join
stri_paste = stri_join
stri_c_list = stri_join_list
stri_paste_list = stri_join_list
