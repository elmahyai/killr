"""Join and flatten strings.

``str_c`` drops ``None`` pieces, checks the rest with
``stringr._size.size_common``, then calls ``stringi.stri_c``. A length-1
vector recycles. Any other mismatch raises. ``str_flatten`` and
``str_flatten_comma`` call ``stringi.stri_flatten``. The Oxford-comma
check calls ``stri_detect_regex`` and ``stri_replace_first_regex``.
"""

from __future__ import annotations

import math

from stringi import stri_c, stri_detect_regex, stri_flatten, stri_replace_first_regex
from stringi._na import is_na
from stringr._size import size_common


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


def _check_bool(value: object, arg: str) -> bool:
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes)):
        if len(value) == 1:
            return _check_bool(value[0], arg)
        raise ValueError(f"`{arg}` must be `TRUE` or `FALSE`, not a logical vector.")
    if value is True or value is False:
        return value
    if value is None:
        raise ValueError(f"`{arg}` must be `TRUE` or `FALSE`, not `NULL`.")
    if is_na(value) or (isinstance(value, float) and math.isnan(value)):
        raise ValueError(f"`{arg}` must be `TRUE` or `FALSE`, not `NA`.")
    if isinstance(value, int) and not isinstance(value, bool):
        raise ValueError(f"`{arg}` must be `TRUE` or `FALSE`, not the number {value}.")
    if isinstance(value, float):
        shown = str(int(value)) if value.is_integer() else str(value)
        raise ValueError(f"`{arg}` must be `TRUE` or `FALSE`, not the number {shown}.")
    raise ValueError(f"`{arg}` must be `TRUE` or `FALSE`.")


def _pieces(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        return [value]
    return list(value)


def _missing(value: object) -> bool:
    if value is None or is_na(value):
        return True
    return isinstance(value, float) and math.isnan(value)


def str_c(*args, sep="", collapse=None):
    """Join vectors element by element, then optionally collapse the rows.

    ``None`` arguments are dropped before the size check. ``sep`` and
    ``collapse`` must be single strings; ``collapse`` may be ``None``.
    """

    separator = _check_string(sep, allow_null=False, arg="sep")
    between = _check_string(collapse, allow_null=True, arg="collapse")
    dots = [arg for arg in args if arg is not None]
    size_common(*dots)
    return stri_c(*dots, sep=separator, collapse=between)


def str_flatten(string, collapse="", last=None, na_rm=False):
    """Join one vector into a single string.

    ``na_rm`` is R's ``na.rm``. When ``last`` is set and at least two
    pieces remain, the final separator is ``last`` instead of ``collapse``.
    The result is a length-1 list. ``None`` flattens to one empty string.
    """

    piece = _check_string(collapse, allow_null=False, arg="collapse")
    ending = _check_string(last, allow_null=True, arg="last")
    drop = _check_bool(na_rm, "na.rm")
    values = _pieces(string)
    if drop:
        values = [item for item in values if not _missing(item)]
    count = len(values)
    if ending is not None and count >= 2:
        head = values[: count - 2]
        tail = stri_c(values[count - 2], ending, values[count - 1])
        values = head + list(tail)
    return stri_flatten(values, collapse=piece)


def str_flatten_comma(string, last=None, na_rm=False):
    """Flatten with ``", "``, and drop an Oxford comma for two pieces.

    The length used for that comma is the length before missing values
    are removed. ``na_rm`` is R's ``na.rm``.
    """

    ending = _check_string(last, allow_null=True, arg="last")
    drop = _check_bool(na_rm, "na.rm")
    if len(_pieces(string)) == 2 and ending is not None:
        hit = stri_detect_regex(ending, "^,")
        matched = hit[0] if isinstance(hit, list) else hit
        if matched is True:
            replaced = stri_replace_first_regex(ending, "^,", "")
            ending = replaced[0] if isinstance(replaced, list) else replaced
    return str_flatten(string, ", ", last=ending, na_rm=drop)
