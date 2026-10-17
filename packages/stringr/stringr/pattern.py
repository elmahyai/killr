"""Modifier objects that tell a stringr search which stringi engine to use.

A plain character vector is an ICU regular expression. ``""`` is the empty
pattern. ``fixed``, ``coll``, ``regex``, and ``boundary`` carry the option
list that stringi expects.
"""

from __future__ import annotations

import warnings

from stringi import stri_opts_brkiter, stri_opts_collator, stri_opts_fixed, stri_opts_regex
from stringi._na import NA, is_na


_BOUNDARY_TYPES = ("character", "line_break", "sentence", "word")


class Pattern(list):
    """A character vector with stringi options and a match kind."""

    def __init__(self, values: list, options: dict, kind: str) -> None:
        super().__init__(values)
        self.options = options
        self.kind = kind

    def __getitem__(self, index):
        item = super().__getitem__(index)
        if isinstance(index, int):
            return Pattern([item], self.options, self.kind)
        return Pattern(list(item), self.options, self.kind)

    def __repr__(self) -> str:
        return f"Pattern({list(self)!r}, kind={self.kind!r}, options={self.options!r})"


def pattern_type(pattern: object) -> str:
    """Return ``fixed``, ``coll``, ``regex``, ``bound``, or ``empty``."""

    if isinstance(pattern, Pattern):
        return pattern.kind
    values = as_strings(pattern, bare=True)
    if any(is_na(value) for value in values):
        raise ValueError("pattern can not contain NAs.")
    if len(values) == 1 and values[0] == "":
        return "empty"
    return "regex"


def pattern_opts(pattern: object) -> dict | None:
    """The option list stored on a modifier, or ``None`` for a plain pattern.

    The empty string is the one input whose options are a character
    boundary, matching ``opts()`` in the R sources.
    """

    if isinstance(pattern, Pattern):
        return pattern.options
    if isinstance(pattern, str) and pattern == "":
        return stri_opts_brkiter(type="character")
    if isinstance(pattern, list) and pattern == [""]:
        return stri_opts_brkiter(type="character")
    return None


def as_strings(pattern: object, bare: bool = False) -> list:
    """The character vector inside ``pattern``.

    A bare string is a length-1 vector. ``bare=True`` does not warn; the
    modifier constructors warn when they have to coerce an object.
    """

    if isinstance(pattern, Pattern):
        return list(pattern)
    if isinstance(pattern, str) or is_na(pattern):
        return [pattern]
    if isinstance(pattern, (list, tuple)):
        return list(pattern)
    if bare:
        raise TypeError("pattern must be a character vector.")
    warnings.warn("Coercing `pattern` to a plain character vector.", stacklevel=2)
    return [str(pattern)]


def _check_bool(value: object, allow_na: bool = False) -> None:
    if value is True or value is False:
        return
    if allow_na and is_na(value):
        return
    raise ValueError("`TRUE` or `FALSE` is required.")


def _arg_match(value: object, choices: tuple[str, ...]) -> str:
    """Keep an exact choice. rlang::arg_match rejects a unique prefix."""

    if isinstance(value, str) and value in choices:
        return value
    quoted = [f'"{choice}"' for choice in choices]
    if len(quoted) == 1:
        shown = quoted[0]
    else:
        shown = ", ".join(quoted[:-1]) + ", or " + quoted[-1]
    if isinstance(value, str):
        got = f'"{value}"'
    else:
        got = repr(value)
    raise ValueError(f"`type` must be one of {shown}, not {got}.")


def fixed(pattern: object, ignore_case: bool = False) -> Pattern:
    """Compare ``pattern`` as literal text."""

    values = _bare_character(pattern)
    _check_bool(ignore_case)
    options = stri_opts_fixed(case_insensitive=ignore_case)
    return Pattern(values, options, "fixed")


def coll(pattern: object, ignore_case: bool = False, locale: str = "en", **kwargs) -> Pattern:
    """Compare ``pattern`` with Unicode collation. The default locale is English."""

    values = _bare_character(pattern)
    _check_bool(ignore_case)
    if not isinstance(locale, str):
        raise ValueError("`locale` must be a single string.")
    strength = kwargs.pop("strength", None)
    if strength is None:
        strength = 2 if ignore_case else 3
    options = stri_opts_collator(strength=strength, locale=locale, **kwargs)
    return Pattern(values, options, "coll")


def regex(
    pattern: object,
    ignore_case: bool = False,
    multiline: bool = False,
    comments: bool = False,
    dotall: bool = False,
    **kwargs,
) -> Pattern:
    """An ICU regular expression with explicit flags."""

    values = _bare_character(pattern)
    _check_bool(ignore_case)
    _check_bool(multiline)
    _check_bool(comments)
    _check_bool(dotall)
    options = stri_opts_regex(
        case_insensitive=ignore_case,
        multiline=multiline,
        comments=comments,
        dotall=dotall,
        **kwargs,
    )
    return Pattern(values, options, "regex")


def boundary(
    type: str = "character",
    skip_word_none: object = NA,
    **kwargs,
) -> Pattern:
    """Match boundaries of ``type`` rather than a text pattern."""

    kind = _arg_match(type, _BOUNDARY_TYPES)
    _check_bool(skip_word_none, allow_na=True)
    if is_na(skip_word_none):
        skip_word_none = kind == "word"
    options = stri_opts_brkiter(type=kind, skip_word_none=skip_word_none, **kwargs)
    return Pattern([NA], options, "bound")


def _bare_character(pattern: object) -> list:
    if isinstance(pattern, str) or is_na(pattern):
        return [pattern]
    if isinstance(pattern, Pattern) or not isinstance(pattern, (list, tuple)):
        warnings.warn("Coercing `pattern` to a plain character vector.", stacklevel=3)
        return _as_character(pattern)
    return list(pattern)


def _as_character(pattern: object) -> list:
    """The as.character results these modifiers receive.

    A logical is TRUE or FALSE. NULL is an empty character vector.
    """

    if pattern is None:
        return []
    if pattern is True:
        return ["TRUE"]
    if pattern is False:
        return ["FALSE"]
    if isinstance(pattern, Pattern):
        return [NA if is_na(value) else str(value) for value in pattern]
    return [str(pattern)]
