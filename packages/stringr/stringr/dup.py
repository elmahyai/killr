"""Duplicate strings.

``str_dup`` recycles with ``vctrs.vec_recycle_common``, then calls
``stringi.stri_dup``. ``NULL`` (``None``) does not take part in that
recycle. A real length-zero vector does, and ``stringr._size.size_common``
rejects it when the other side is longer than one, which is the same
rule. With ``sep`` set, each copy is joined by ``paste`` rules: a
missing string becomes the letters ``NA``, and the index is taken from
the original ``string``, not the recycled one.
"""

from __future__ import annotations

import math

from rlang import set_names
from stringi import stri_dup
from stringi._na import NA, is_na
from stringr._size import size_common
from vctrs import vec_recycle_common


def _length(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        return 1
    return len(value)


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


def _names_after_recycle(string: object, times: object, out_length: int) -> list | None:
    names = getattr(string, "names", None)
    if not names or out_length == 0 or len(names) != _length(string):
        return None
    if _length(string) == 1 and out_length != 1:
        return list(names) * out_length
    if len(names) == out_length:
        return list(names)
    return None


def _with_names(out: list, names: list | None) -> list:
    if not names or len(names) != len(out):
        return list(out)
    return set_names(list(out), names)


def _rep_times(count: object) -> int:
    """R's ``rep`` count. A negative or missing count is an error."""

    if count is None or is_na(count):
        raise ValueError("invalid 'times' argument")
    if isinstance(count, bool):
        number = int(count)
    elif isinstance(count, int):
        number = count
    elif isinstance(count, float):
        if math.isnan(count) or math.isinf(count):
            raise ValueError("invalid 'times' argument")
        number = math.trunc(count)
    else:
        raise ValueError("invalid 'times' argument")
    if number < 0:
        raise ValueError("invalid 'times' argument")
    return number


def _paste_atom(element: object) -> str:
    """One piece as ``paste`` would print it, including the letters NA."""

    coerced = stri_dup(element, 1)
    text = coerced[0]
    if text is NA or is_na(text):
        return "NA"
    return text


def _recycle(string: object, times: object):
    """Match ``vec_recycle_common`` for ``NULL`` and for a length-zero vector.

    ``None`` stays ``None``. Any other pair is checked with ``size_common``
    and then recycled by ``vec_recycle_common``.
    """

    if string is None or times is None:
        return string, times
    size_common(string, times, names=["string", "times"])
    return vec_recycle_common(string, times)


def str_dup(string, times, sep=None):
    """Duplicate each string ``times`` times.

    ``sep=None`` is R's ``NULL`` and calls ``stri_dup``. Any other ``sep``
    is inserted between copies. A length-1 ``string`` is not indexed past
    its original length, so ``str_dup("ab", [1, 2, 3], sep="-")`` raises
    ``subscript out of bounds``.
    """

    recycled_string, recycled_times = _recycle(string, times)
    separator = _check_string(sep, allow_null=True, arg="sep")
    if separator is None:
        out = stri_dup(recycled_string, recycled_times)
        names = _names_after_recycle(string, times, len(out))
        return _with_names(out, names)

    if string is None or _length(string) == 0:
        return []
    if times is None:
        raise ValueError("invalid 'times' argument")

    original = list(string) if isinstance(string, (list, tuple)) else [string]
    counts = list(recycled_times)
    out = []
    for index, count in enumerate(counts):
        if index >= len(original):
            raise ValueError("subscript out of bounds")
        copies = _rep_times(count)
        text = _paste_atom(original[index])
        out.append("" if copies == 0 else separator.join([text] * copies))
    names = _names_after_recycle(string, times, len(out))
    return _with_names(out, names)
