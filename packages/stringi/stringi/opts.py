"""Option lists for stringi searchers.

Each builder returns a dict of the settings that were actually passed.
An omitted argument is left out, which is how the R functions treat a
missing formal even when that formal has a default. ``None`` is R's
``NULL`` and drops the name. A list or tuple is one replacement value:
an empty one is an error, and a longer one warns and keeps its first
element, as R's ``[<-`` does.
"""

from __future__ import annotations

import warnings

from stringi._na import is_na

_COLLATOR = (
    "locale",
    "strength",
    "alternate_shifted",
    "french",
    "uppercase_first",
    "case_level",
    "normalization",
    "normalisation",
    "numeric",
)
_REGEX = (
    "case_insensitive",
    "comments",
    "dotall",
    "dot_all",
    "literal",
    "multiline",
    "multi_line",
    "unix_lines",
    "uword",
    "error_on_unknown_escapes",
    "time_limit",
    "stack_limit",
)
_BRKITER = (
    "type",
    "locale",
    "skip_word_none",
    "skip_word_number",
    "skip_word_letter",
    "skip_word_kana",
    "skip_word_ideo",
    "skip_line_soft",
    "skip_line_hard",
    "skip_sentence_term",
    "skip_sentence_sep",
)
_FIXED = ("case_insensitive", "overlap")


def stri_opts_collator(*args, **kwargs) -> dict:
    """Collator settings for locale-aware comparison and search.

    ``normalisation`` is stored under ``normalization``. When both are
    passed, ``normalization`` is the one that is kept.
    """
    bound = _bind(_COLLATOR, args, kwargs)
    opts: dict = {}
    for name in (
        "locale",
        "strength",
        "alternate_shifted",
        "french",
        "uppercase_first",
        "case_level",
        "numeric",
    ):
        if name in bound:
            _assign(opts, name, bound[name])
    if "normalization" in bound:
        _assign(opts, "normalization", bound["normalization"])
    elif "normalisation" in bound:
        _assign(opts, "normalization", bound["normalisation"])
    return opts


def stri_opts_regex(*args, **kwargs) -> dict:
    """Regex matcher settings.

    ``dot_all`` is stored as ``dotall`` and ``multi_line`` as ``multiline``.
    The primary name wins when both the primary and its alias are passed.
    ``stack_limit`` is recorded before ``time_limit``.
    """
    bound = _bind(_REGEX, args, kwargs)
    opts: dict = {}
    for name in (
        "case_insensitive",
        "comments",
        "literal",
        "unix_lines",
        "uword",
        "error_on_unknown_escapes",
        "stack_limit",
        "time_limit",
    ):
        if name in bound:
            _assign(opts, name, bound[name])
    if "dotall" in bound:
        _assign(opts, "dotall", bound["dotall"])
    elif "dot_all" in bound:
        _assign(opts, "dotall", bound["dot_all"])
    if "multiline" in bound:
        _assign(opts, "multiline", bound["multiline"])
    elif "multi_line" in bound:
        _assign(opts, "multiline", bound["multi_line"])
    return opts


def stri_opts_brkiter(*args, **kwargs) -> dict:
    """Break-iterator settings for text boundary analysis.

    Omitted ``skip_*`` settings are absent. Callers treat an absent skip
    as false.
    """
    bound = _bind(_BRKITER, args, kwargs)
    opts: dict = {}
    for name in _BRKITER:
        if name in bound:
            _assign(opts, name, bound[name])
    return opts


def stri_opts_fixed(*args, **kwargs) -> dict:
    """Fixed-pattern search settings.

    ``case_insensitive`` is a one-code-point case mapping. ``overlap``
    asks extract, locate, and count to report overlapping matches.
    """
    bound = _bind(_FIXED, args, kwargs)
    opts: dict = {}
    for name in _FIXED:
        if name in bound:
            _assign(opts, name, bound[name])
    return opts


def _bind(formals: tuple[str, ...], args: tuple, kwargs: dict) -> dict:
    """Match a call the way R matches formals.

    Exact names are taken first, then unique prefixes. Positional values
    fill the formals that are still open. An ambiguous prefix raises
    ``argument N matches multiple formal arguments``. Anything left over
    raises ``unused argument``.
    """
    formal_set = set(formals)
    bound: dict = {}
    unused: list[str] = []
    items = list(kwargs.items())

    for key, value in items:
        if key in formal_set:
            bound[key] = value

    for index, (key, value) in enumerate(items):
        if key in formal_set:
            continue
        matches = [name for name in formals if name not in bound and name.startswith(key)]
        if len(matches) > 1:
            argument = len(args) + index + 1
            raise TypeError(f"argument {argument} matches multiple formal arguments")
        if len(matches) == 1:
            bound[matches[0]] = value
            continue
        unused.append(f"{key} = {_r_deparse(value)}")

    open_names = [name for name in formals if name not in bound]
    if len(args) > len(open_names):
        extra = [_r_deparse(value) for value in args[len(open_names) :]]
        unused = extra + unused
    for name, value in zip(open_names, args, strict=False):
        bound[name] = value

    if unused:
        label = "argument" if len(unused) == 1 else "arguments"
        raise TypeError(f"unused {label} ({', '.join(unused)})")
    return bound


def _assign(opts: dict, name: str, value: object) -> None:
    """Store one setting with R's single-name ``[<-`` rules."""
    if value is None:
        opts.pop(name, None)
        return
    items = _replacement_items(value)
    if items is None:
        opts[name] = value
        return
    if len(items) == 0:
        raise ValueError("replacement has length zero")
    if len(items) != 1:
        warnings.warn(
            "number of items to replace is not a multiple of replacement length",
            UserWarning,
            stacklevel=3,
        )
    opts[name] = items[0]


def _replacement_items(value: object) -> list | None:
    """Elements of a list or tuple. Strings and other scalars stay whole."""
    if isinstance(value, (str, bytes, bytearray)):
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    return None


def _r_deparse(value: object) -> str:
    """Render a literal the way R deparses it in an unused-argument error."""
    if is_na(value):
        return "NA"
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    if value is None:
        return "NULL"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, (list, tuple)):
        inner = ", ".join(_r_deparse(item) for item in value)
        return f"c({inner})"
    return repr(value)
