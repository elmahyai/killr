"""Selection helper from tidyselect 1.2.1.

``starts_with`` returns the 1-based positions of names that start with a
literal prefix. A name that matches several prefixes is returned once for
each prefix, in prefix order. ``ignore_case`` is R's ``ignore.case``.
``vars`` is the character vector of names. ``None`` reads the selection
context, which is empty until a selecting function sets it.
"""

from __future__ import annotations

import math

from tidyselect.helpers_misc import TidyselectError, _peek

_TRUE_WORDS = {"TRUE", "True", "true", "T"}
_FALSE_WORDS = {"FALSE", "False", "false", "F"}
_MATCH_ERROR = "`match` must be a character vector of non empty strings."

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


def starts_with(match, ignore_case=True, vars=None):
    """Return positions of names that start with each prefix in ``match``.

    ``ignore_case`` defaults to true and lowercases names and prefixes with
    R's ``tolower`` before the comparison. The prefix is literal, so a dot
    or a bracket is not a regular expression. ``vars`` omitted is the
    out-of-context error. A missing prefix matches nothing.
    """
    patterns = _as_match(match)
    names = _as_vars(vars)
    if _as_flag(ignore_case):
        patterns = [_tolower(pattern) for pattern in patterns]
        names = [_tolower(name) for name in names]
    found = []
    for pattern in patterns:
        found.extend(_which_prefix(pattern, names))
    return found


def _as_match(match):
    """R's ``check_match``: a character vector whose strings are non-empty.

    ``nzchar(NA_character_)`` is true, so a missing string is allowed.
    An empty string is not. ``NULL`` is not a character vector.
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
    if vars is None:
        _peek("starts_with")
    if isinstance(vars, str):
        return [vars]
    if isinstance(vars, (list, tuple)) and all(
        item is None or isinstance(item, str) for item in vars
    ):
        return list(vars)
    raise TidyselectError("`vars` must be a character vector")


def _tolower(text):
    if text is None:
        return None
    if text.isascii():
        return text.lower()
    return "".join(_TOLOWER_FIX.get(char, char.lower()) for char in text)


def _which_prefix(needle, haystack):
    """``which(needle == substr(haystack, 1, nchar(needle)))``.

    A missing needle matches nothing: ``nchar(NA)`` is missing, ``substr``
    is missing, and ``which`` drops every missing comparison. A missing
    name is dropped the same way.
    """
    if needle is None:
        return []
    width = len(needle)
    return [
        position
        for position, name in enumerate(haystack, start=1)
        if name is not None and name[:width] == needle
    ]


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
