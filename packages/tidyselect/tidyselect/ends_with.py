"""Selection helper from tidyselect 1.2.1.

``ends_with`` returns the 1-based positions of names that end with a
literal suffix. A name that matches several suffixes is returned once
for each suffix, in suffix order. ``ignore_case`` is R's ``ignore.case``.
``vars`` is the character vector of names. ``None`` reads the selection
context, which is empty until a selecting function sets it.
"""

from __future__ import annotations

import math

from tidyselect.helpers_misc import TidyselectError, _as_character_double, _peek

_TRUE_WORDS = {"TRUE", "True", "true", "T"}
_FALSE_WORDS = {"FALSE", "False", "false", "F"}
_MATCH_ERROR = "`match` must be a character vector of non empty strings."
_NCHAR_ERROR = "'nchar()' requires a character vector"

# R's tolower is the C library's towlower. These six letters are the BMP
# mappings that differ from str.lower() in the en_US.UTF-8 locale.
_TOLOWER_FIX = {
    "\u0130": "i",
    "\u1c89": "\u1c8a",
    "\ua7cb": "\u0264",
    "\ua7cc": "\ua7cd",
    "\ua7da": "\ua7db",
    "\ua7dc": "\u019b",
}


def ends_with(match, ignore_case=True, vars=None):
    """Return positions of names that end with each literal string in ``match``.

    ``ignore_case`` defaults to true and lowercases names and suffixes with
    R's ``tolower`` before the comparison. The suffix is literal, so a dot
    is not a regular expression. ``vars`` omitted is the out-of-context
    error. A missing suffix matches nothing.
    """
    patterns = _as_match(match)
    if vars is None:
        _peek("ends_with")
    casefold = _as_flag(ignore_case)
    names = _as_vars(vars)
    if casefold:
        patterns = [_tolower(pattern) for pattern in patterns]
        names = [_tolower(name) for name in names]
    found = []
    for pattern in patterns:
        found.extend(_suffix_positions(pattern, names))
    return found


def _as_match(match):
    """R's ``check_match``: a character vector whose strings are non-empty.

    ``nzchar(NA_character_)`` is true when ``keepNA`` is false, so a missing
    string is allowed. An empty string is not. A length-zero character
    vector is allowed and selects nothing.
    """
    if isinstance(match, str):
        values = [match]
    elif isinstance(match, (list, tuple)) and all(
        item is None or isinstance(item, str) for item in match
    ):
        values = list(match)
    else:
        raise TidyselectError(_MATCH_ERROR)
    if any(value == "" for value in values):
        raise TidyselectError(_MATCH_ERROR)
    return values


def _as_vars(vars):
    """Names as R sees them after ``tolower`` or ``nchar`` coerces.

    A string is one name. A list or tuple is a vector. ``None`` inside
    that vector is a missing name. Numbers, logicals, complex values,
    and raw bytes are coerced with R's ``as.character``.
    """
    if isinstance(vars, str):
        return [vars]
    if isinstance(vars, (bytes, bytearray)):
        return [f"{byte:02x}" for byte in vars]
    if isinstance(vars, (list, tuple)):
        return [_as_character_element(item) for item in vars]
    return [_as_character_element(vars)]


def _as_character_element(item):
    if item is None or isinstance(item, str):
        return item
    if isinstance(item, bool):
        return "TRUE" if item else "FALSE"
    if isinstance(item, int):
        return str(item)
    if isinstance(item, float):
        return _as_character_double(item)
    if isinstance(item, complex):
        return _as_character_complex(item)
    if isinstance(item, (bytes, bytearray)):
        if len(item) == 1:
            return f"{item[0]:02x}"
        raise TidyselectError(_NCHAR_ERROR)
    raise TidyselectError(_NCHAR_ERROR)


def _as_character_complex(value):
    """R's ``as.character`` for one complex value.

    ``NA_complex_`` is a missing string. A finite value is the real part,
    a sign, the imaginary part, and ``i``, with no spaces.
    """
    real = value.real
    imag = value.imag
    if math.isnan(real) and math.isnan(imag):
        return None
    left = _as_character_double(real)
    right = _as_character_double(imag)
    if right.startswith("-"):
        return f"{left}{right}i"
    return f"{left}+{right}i"


def _tolower(text):
    if text is None:
        return None
    if text.isascii():
        return text.lower()
    return "".join(_TOLOWER_FIX.get(char, char.lower()) for char in text)


def _suffix_positions(pattern, names):
    """``which(pattern == substr(names, pmax(1, length - n + 1), length))``.

    A missing pattern compares unequal to every name, including a missing
    name, so ``which`` drops the whole vector. A missing name is dropped
    the same way.
    """
    if pattern is None:
        return []
    n = len(pattern)
    found = []
    for position, name in enumerate(names, start=1):
        if name is None:
            continue
        length = len(name)
        start = max(1, length - n + 1)
        if name[start - 1 : length] == pattern:
            found.append(position)
    return found


def _as_flag(value):
    """R's ``if (ignore.case)`` on one value."""
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise TidyselectError("argument is of length zero")
        if len(value) > 1:
            raise TidyselectError("the condition has length > 1")
        inner = value[0]
        if inner is None:
            raise TidyselectError("missing value where TRUE/FALSE needed")
        if isinstance(inner, (list, tuple, dict)):
            raise TidyselectError("argument is not interpretable as logical")
        return _scalar_flag(inner)
    if value is None:
        raise TidyselectError("argument is of length zero")
    return _scalar_flag(value)


def _scalar_flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float):
        if math.isnan(value):
            raise TidyselectError("argument is not interpretable as logical")
        return value != 0.0
    if isinstance(value, complex):
        if math.isnan(value.real) or math.isnan(value.imag):
            raise TidyselectError("argument is not interpretable as logical")
        return value.real != 0.0 or value.imag != 0.0
    if isinstance(value, str):
        if value in _TRUE_WORDS:
            return True
        if value in _FALSE_WORDS:
            return False
        raise TidyselectError("argument is not interpretable as logical")
    if isinstance(value, (bytes, bytearray)):
        if len(value) == 0:
            raise TidyselectError("argument is of length zero")
        if len(value) > 1:
            raise TidyselectError("the condition has length > 1")
        return value[0] != 0
    raise TidyselectError("argument is not interpretable as logical")
