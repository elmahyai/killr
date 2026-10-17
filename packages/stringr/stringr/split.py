"""Split strings into pieces, matching stringr 1.6.0.

``str_split`` dispatches on ``pattern_type`` and passes ``pattern_opts`` to
the finished stringi splitter. A plain string is a regular expression. The
empty pattern is a character boundary. ``str_split_fixed`` pads short rows
with ``""``. A positive ``str_split_i`` asks for one extra piece and pads
with :data:`stringi._na.NA`, so a missing piece stays missing.
"""

from __future__ import annotations

from stringi import (
    stri_opts_brkiter,
    stri_split_boundaries,
    stri_split_coll,
    stri_split_fixed,
    stri_split_regex,
)
from stringi._na import NA, is_na

from stringr._size import check_lengths
from stringr.pattern import Pattern, pattern_opts, pattern_type


def _is_positive_inf(value: object) -> bool:
    return isinstance(value, float) and value == float("inf")


def _shown_number(value: object) -> str:
    if isinstance(value, float) and value.is_integer() and abs(value) < 10**15:
        return str(int(value))
    return str(value)


def _not_whole(value: object, arg: str) -> None:
    if value is True:
        shown = "`TRUE`"
    elif value is False:
        shown = "`FALSE`"
    elif is_na(value):
        shown = "`NA`"
    elif isinstance(value, float) and value == float("inf"):
        shown = "`Inf`"
    elif isinstance(value, float) and value == float("-inf"):
        shown = "`-Inf`"
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        shown = f"the number {_shown_number(value)}"
    else:
        shown = repr(value)
    raise ValueError(f"`{arg}` must be a whole number, not {shown}.")


def _whole(value: object, arg: str) -> int:
    """R's ``check_number_whole``: one integer in the 32-bit range."""

    if isinstance(value, bool) or is_na(value) or not isinstance(value, (int, float)):
        _not_whole(value, arg)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            _not_whole(value, arg)
        if not value.is_integer():
            _not_whole(value, arg)
    number = int(value)
    if number < -2147483647 or number > 2147483647:
        _not_whole(value, arg)
    return number


def _check_positive_integer(n: object) -> None:
    """``Inf`` is allowed. Any other ``n`` is a whole number of at least 1."""

    if _is_positive_inf(n):
        return
    number = _whole(n, "n")
    if number < 1:
        raise ValueError(
            f"`n` must be a number larger than 1, not the number {_shown_number(n)}."
        )


def _split_count(n: object) -> int:
    """``Inf`` becomes stringi's unlimited count, ``-1``."""

    if _is_positive_inf(n):
        return -1
    number = _whole(n, "n")
    if number < 1:
        raise ValueError(
            f"`n` must be a number larger than 1, not the number {_shown_number(n)}."
        )
    return number


def _check_simplify(simplify: object) -> None:
    if simplify is True or simplify is False or is_na(simplify):
        return
    if isinstance(simplify, (int, float)) and not isinstance(simplify, bool):
        raise ValueError(
            f"`simplify` must be `TRUE`, `FALSE`, or `NA`, not the number {_shown_number(simplify)}."
        )
    raise ValueError("`simplify` must be `TRUE`, `FALSE`, or `NA`.")


def _check_string(string: object) -> None:
    if isinstance(string, str):
        return
    if is_na(string):
        raise ValueError("`string` must be a single string, not a character `NA`.")
    if isinstance(string, (list, tuple)):
        if len(string) == 1 and isinstance(string[0], str):
            return
        if len(string) == 1 and is_na(string[0]):
            raise ValueError("`string` must be a single string, not a character `NA`.")
        if len(string) == 0:
            raise ValueError("`string` must be a single string, not an empty character vector.")
        if len(string) > 1 and all(isinstance(item, str) or is_na(item) for item in string):
            raise ValueError("`string` must be a single string, not a character vector.")
    raise ValueError("`string` must be a single string.")


def _texts(string: object) -> object:
    """R's ``NULL`` string is an empty character vector."""

    if string is None:
        return []
    return string


def _pattern_vector(pattern: object) -> object:
    """A tuple is a character vector. ``pattern_opts`` only matches a list."""

    if isinstance(pattern, tuple):
        return list(pattern)
    return pattern


def _search_text(pattern: object) -> object:
    if isinstance(pattern, Pattern):
        return list(pattern)
    return pattern


def _dispatch(string: object, pattern: object, n: int, simplify: object) -> list:
    kind = pattern_type(pattern)
    opts = pattern_opts(pattern)
    if kind == "empty" or kind == "bound":
        if kind == "empty" and opts is None:
            opts = stri_opts_brkiter(type="character")
        return stri_split_boundaries(string, n=n, simplify=simplify, opts_brkiter=opts)
    text = _search_text(pattern)
    if kind == "fixed":
        return stri_split_fixed(string, text, n=n, simplify=simplify, opts_fixed=opts)
    if kind == "regex":
        return stri_split_regex(string, text, n=n, simplify=simplify, opts_regex=opts)
    if kind == "coll":
        return stri_split_coll(string, text, n=n, simplify=simplify, opts_collator=opts)
    raise ValueError(f"unknown pattern type {kind!r}")


def str_split(string: object, pattern: object, n: object = float("inf"), simplify: object = False) -> list:
    """Split each string into a list of pieces.

    ``simplify=False`` returns a list of character vectors and does not pad.
    ``simplify=True`` returns one row per string, padded with ``""``.
    ``simplify`` equal to :data:`stringi._na.NA` pads with a missing value.
    """

    check_lengths(string, pattern)
    count = _split_count(n)
    _check_simplify(simplify)
    return _dispatch(_texts(string), _pattern_vector(pattern), count, simplify)


def str_split_1(string: object, pattern: object) -> list:
    """Split one string and return that character vector."""

    _check_string(string)
    pieces = str_split(string, pattern)
    if not pieces:
        raise IndexError("subscript out of bounds")
    return pieces[0]


def str_split_fixed(string: object, pattern: object, n: object) -> list:
    """Split into ``n`` columns, padding short rows with ``""``."""

    check_lengths(string, pattern)
    _check_positive_integer(n)
    return str_split(string, pattern, n=n, simplify=True)


def str_split_i(string: object, pattern: object, i: object) -> list:
    """Return the ``i``-th piece of each string. Negative ``i`` counts from the end.

    A positive index splits with ``n = i + 1`` and ``simplify`` missing, so
    the selected column is one finished piece and a missing piece is
    :data:`stringi._na.NA`.
    """

    index = _whole(i, "i")
    if index > 0:
        rows = str_split(string, pattern, n=index + 1, simplify=NA)
        chosen = index - 1
        return [row[chosen] if chosen < len(row) else NA for row in rows]
    if index < 0:
        want = -index
        rows = str_split(string, pattern)
        out = []
        for row in rows:
            if want > len(row):
                out.append(NA)
            else:
                out.append(row[len(row) - want])
        return out
    raise ValueError("`i` must not be 0.")
