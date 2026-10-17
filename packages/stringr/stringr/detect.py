"""Presence tests from stringr 1.6.0: detect, starts, ends, which, like, ilike.

A plain character vector is an ICU regular expression. ``fixed``, ``coll``,
and ``regex`` are :class:`~stringr.pattern.Pattern` objects. ``""`` and
``boundary()`` are rejected here; ``str_count`` is the function that counts
them. ``str_starts`` and ``str_ends`` wrap a regular expression as
``^(pattern)`` and ``(pattern)$`` so that ``|`` stays inside the anchor.
``paste0`` writes a missing piece as the letters ``NA``.
"""

from __future__ import annotations

from cli import cli_abort
from lifecycle import deprecate_warn, deprecated, is_present
from stringi import (
    stri_detect_coll,
    stri_detect_fixed,
    stri_detect_regex,
    stri_endswith_coll,
    stri_endswith_fixed,
    stri_replace_all_regex,
    stri_startswith_coll,
    stri_startswith_fixed,
)
from stringi._na import NA, is_na

from stringr._size import check_lengths, no_boundary, no_empty
from stringr.pattern import Pattern, pattern_opts, pattern_type, regex


class _Named(list):
    """A character or logical vector that still carries R names."""

    def __init__(self, values, names) -> None:
        super().__init__(values)
        self.names = list(names)


def _check_bool(value: object) -> None:
    if value is True or value is False:
        return
    raise ValueError("`TRUE` or `FALSE` is required.")


def _check_character(pattern: object) -> None:
    if isinstance(pattern, Pattern):
        return
    if is_na(pattern) or isinstance(pattern, str):
        return
    if isinstance(pattern, (list, tuple)):
        for item in pattern:
            if is_na(item) or isinstance(item, str):
                continue
            raise TypeError("`pattern` must be a character vector.")
        return
    raise TypeError("`pattern` must be a character vector.")


def _length(value: object) -> int:
    if value is None:
        return 0
    if is_na(value) or isinstance(value, (str, bool, int, float)):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    raise TypeError(f"cannot take the length of {type(value).__name__}")


def _pieces(pattern: object) -> list:
    if is_na(pattern) or isinstance(pattern, str):
        return [pattern]
    return list(pattern)


def _preserve_names(string: object, pattern: object, out: list):
    values = list(out)
    pattern_length = _length(pattern)
    if not (pattern_length == 1 or pattern_length == _length(string)):
        return values
    names = getattr(string, "names", None)
    if names is None:
        return values
    names = list(names)
    if len(names) != len(values):
        return values
    return _Named(values, names)


def _anchor(pieces: list, at_start: bool) -> list:
    """``paste0`` around the pattern. A missing piece becomes the letters NA."""

    anchored = []
    for piece in pieces:
        text = "NA" if is_na(piece) else piece
        if at_start:
            anchored.append("^(" + text + ")")
        else:
            anchored.append("(" + text + ")$")
    return anchored


def _detect(string: object, pattern: object, negate: bool, kind: str) -> list:
    opts = pattern_opts(pattern)
    if kind == "fixed":
        return stri_detect_fixed(string, pattern, negate=negate, opts_fixed=opts)
    if kind == "coll":
        return stri_detect_coll(string, pattern, negate=negate, opts_collator=opts)
    if kind == "regex":
        return stri_detect_regex(string, pattern, negate=negate, opts_regex=opts)
    raise ValueError(f"unknown pattern type {kind}")


def _reject_modifier(pattern: object) -> None:
    if isinstance(pattern, Pattern):
        cli_abort("{.arg pattern} must be a plain string, not a stringr modifier.")


def str_detect(string, pattern, negate: bool = False):
    """True where ``pattern`` matches ``string``.

    The result has the common length of ``string`` and ``pattern``. A missing
    string is missing. A length-1 argument is recycled, including down to
    length 0. Names on ``string`` are kept when ``pattern`` has length 1 or
    the same length as ``string``.
    """

    check_lengths(string, pattern)
    _check_bool(negate)
    kind = pattern_type(pattern)
    if kind == "empty":
        no_empty()
    if kind == "bound":
        no_boundary()
    out = _detect(string, pattern, negate, kind)
    return _preserve_names(string, pattern, out)


def str_starts(string, pattern, negate: bool = False):
    """True where ``string`` starts with ``pattern``.

    A regular expression is wrapped as ``^(pattern)`` and searched with
    ``stri_detect_regex``. Fixed and collation patterns use the start
    matchers and the modifier's option list.
    """

    check_lengths(string, pattern)
    _check_bool(negate)
    kind = pattern_type(pattern)
    if kind == "empty":
        no_empty()
    if kind == "bound":
        no_boundary()
    opts = pattern_opts(pattern)
    if kind == "fixed":
        out = stri_startswith_fixed(string, pattern, negate=negate, opts_fixed=opts)
    elif kind == "coll":
        out = stri_startswith_coll(string, pattern, negate=negate, opts_collator=opts)
    else:
        out = stri_detect_regex(
            string,
            _anchor(_pieces(pattern), True),
            negate=negate,
            opts_regex=opts,
        )
    return _preserve_names(string, pattern, out)


def str_ends(string, pattern, negate: bool = False):
    """True where ``string`` ends with ``pattern``.

    A regular expression is wrapped as ``(pattern)$``. Fixed and collation
    patterns use the end matchers.
    """

    check_lengths(string, pattern)
    _check_bool(negate)
    kind = pattern_type(pattern)
    if kind == "empty":
        no_empty()
    if kind == "bound":
        no_boundary()
    opts = pattern_opts(pattern)
    if kind == "fixed":
        out = stri_endswith_fixed(string, pattern, negate=negate, opts_fixed=opts)
    elif kind == "coll":
        out = stri_endswith_coll(string, pattern, negate=negate, opts_collator=opts)
    else:
        out = stri_detect_regex(
            string,
            _anchor(_pieces(pattern), False),
            negate=negate,
            opts_regex=opts,
        )
    return _preserve_names(string, pattern, out)


def str_which(string, pattern, negate: bool = False):
    """1-based positions where ``str_detect`` is true.

    A missing result is not a match. Names of the true elements are kept
    when detection kept them. No matches on a named result is an empty
    vector that still has a names attribute.
    """

    found = str_detect(string, pattern, negate=negate)
    names = getattr(found, "names", None)
    indices = []
    kept = []
    for index, flag in enumerate(found):
        if flag is True:
            indices.append(index + 1)
            if names is not None:
                kept.append(names[index])
    if names is None:
        return indices
    return _Named(indices, kept)


def like_to_regex(pattern):
    """Turn a SQL ``LIKE`` pattern into an anchored regular expression.

    ``%`` becomes ``.*`` and ``_`` becomes ``.``, unless a backslash or an
    opening bracket sits immediately before that character, or a closing
    bracket sits immediately after it. The result is wrapped with ``^`` and
    ``$``. A missing pattern becomes the letters ``NA`` inside that wrap,
    which is what ``paste0`` does.
    """

    converted = stri_replace_all_regex(pattern, r"(?<!\\|\[)%(?!\])", r"\.\*")
    converted = stri_replace_all_regex(converted, r"(?<!\\|\[)_(?!\])", r"\.")
    return ["^NA$" if is_na(item) else "^" + item + "$" for item in converted]


def _like_detect(string, pattern, ignore_case: bool):
    anchored = regex(like_to_regex(pattern), ignore_case=ignore_case)
    out = stri_detect_regex(string, anchored, opts_regex=pattern_opts(anchored))
    return _preserve_names(string, pattern, out)


def str_like(string, pattern, ignore_case=deprecated()):
    """Match ``string`` the way SQL ``LIKE`` matches.

    The whole string must match. ``ignore_case`` is deprecated: supplying it
    warns, and ``TRUE`` forwards to :func:`str_ilike`. A modifier object is
    rejected. The pattern is not a regular expression and is not ``fixed``.
    """

    check_lengths(string, pattern)
    _check_character(pattern)
    _reject_modifier(pattern)
    if is_present(ignore_case):
        deprecate_warn(
            when="1.6.0",
            what="str_like(ignore_case)",
            details=[
                "`str_like()` is always case sensitive.",
                "Use `str_ilike()` for case insensitive string matching.",
            ],
            package="stringr",
        )
        _check_bool(ignore_case)
        if ignore_case:
            return str_ilike(string, pattern)
    return _like_detect(string, pattern, False)


def str_ilike(string, pattern):
    """Match ``string`` the way SQL ``ILIKE`` matches.

    The same rules as :func:`str_like`, with case ignored.
    """

    check_lengths(string, pattern)
    _check_character(pattern)
    _reject_modifier(pattern)
    return _like_detect(string, pattern, True)
