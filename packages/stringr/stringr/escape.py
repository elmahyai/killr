"""Escape regex metacharacters and reinterpret string bytes.

``str_escape`` calls ``stringi.stri_replace_all_regex``. ``str_conv``
calls ``stringi.stri_conv`` and asks for UTF-8. A bare string is a
length-1 vector. Bytes are a raw vector, which is how an unknown-encoding
R string is stored.
"""

from __future__ import annotations

import math

from stringi import stri_conv, stri_enc_info, stri_replace_all_regex
from stringi._na import is_na
from stringr.length import _as_list, _copy_names

# The R replacement "\\\\\\1" is three backslashes and a 1. stringr's
# fix_replacement turns that into the ICU text \\$1, one escaped
# backslash in front of the captured character.
_METACHARACTERS = "([.^$\\\\|*+?{}\\[\\]()])"
_ESCAPED = "\\\\$1"


def _check_string(value: object, *, allow_null: bool, arg: str) -> str | None:
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes)):
        if len(value) == 1:
            return _check_string(value[0], allow_null=allow_null, arg=arg)
        tail = " or `NULL`" if allow_null else ""
        raise ValueError(f"`{arg}` must be a single string{tail}, not a character vector.")
    if value is None:
        if allow_null:
            return None
        raise ValueError(f"`{arg}` must be a single string, not `NULL`.")
    if is_na(value):
        tail = " or `NULL`" if allow_null else ""
        raise ValueError(f"`{arg}` must be a single string{tail}, not `NA`.")
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        shown = "`TRUE`" if value else "`FALSE`"
        tail = " or `NULL`" if allow_null else ""
        raise ValueError(f"`{arg}` must be a single string{tail}, not {shown}.")
    if isinstance(value, int):
        tail = " or `NULL`" if allow_null else ""
        raise ValueError(f"`{arg}` must be a single string{tail}, not the number {value}.")
    if isinstance(value, float):
        tail = " or `NULL`" if allow_null else ""
        if math.isnan(value):
            raise ValueError(f"`{arg}` must be a single string{tail}, not `NA`.")
        shown = str(int(value)) if value.is_integer() else str(value)
        raise ValueError(f"`{arg}` must be a single string{tail}, not the number {shown}.")
    tail = " or `NULL`" if allow_null else ""
    raise ValueError(f"`{arg}` must be a single string{tail}.")


def str_escape(string):
    """Put a backslash in front of each regular-expression metacharacter.

    The metacharacters are ``. ^ $ \\ | * + ? { } [ ] ( )``. Names on
    ``string`` are kept. A missing string stays missing.
    """

    if string is None:
        return []
    out = stri_replace_all_regex(string, _METACHARACTERS, _ESCAPED)
    return _copy_names(string, out)


def str_conv(string, encoding):
    """Reinterpret ``string`` as ``encoding`` and return UTF-8 text.

    ``encoding`` is one converter name. ``None`` for ``string`` is one
    missing result, matching ``stri_conv(NULL, encoding, "UTF-8")``.
    A ``bytes`` value is a raw vector. Names on a character vector are kept.
    """

    chosen = _check_string(encoding, allow_null=False, arg="encoding")
    try:
        out = stri_conv(string, chosen, "UTF-8")
    except TypeError as exc:
        # stri_encode names its argument str, so a failed conversion
        # raises TypeError instead of the ICU message. Opening the
        # converter here raises that message when the name is unknown.
        if "not callable" not in str(exc):
            raise
        stri_enc_info(chosen)
        raise
    return _copy_names(string, _as_list(out))
