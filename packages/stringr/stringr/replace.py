"""Replace and remove matches, matching stringr 1.6.0.

A string replacement calls the finished stringi replace functions.
A function is different: the match is located, the function sees those
pieces, and the result is written back with ``stri_sub_replace``.
``str_replace_all`` flattens the pieces with ``list_unchop`` and cuts
the flat result back apart with the 1-based ranges from ``chop_index``.
"""

from __future__ import annotations

import math

from stringi import (
    stri_locate_all_boundaries,
    stri_locate_all_coll,
    stri_locate_all_fixed,
    stri_locate_all_regex,
    stri_locate_first_boundaries,
    stri_locate_first_coll,
    stri_locate_first_fixed,
    stri_locate_first_regex,
    stri_replace_all_coll,
    stri_replace_all_fixed,
    stri_replace_all_regex,
    stri_replace_first_coll,
    stri_replace_first_fixed,
    stri_replace_first_regex,
    stri_replace_na,
    stri_sub,
    stri_sub_all,
    stri_sub_replace,
    stri_sub_replace_all,
)
from stringi._na import NA, is_na
from vctrs import list_unchop

from stringr._size import check_lengths, no_boundary, no_empty
from stringr.pattern import Pattern, pattern_opts, pattern_type

_MISSING = object()


class _Named(list):
    """A character vector that still carries its names."""

    def __init__(self, values, names):
        super().__init__(values)
        self.names = list(names)


def str_replace(string, pattern, replacement):
    """Replace the first match in each string.

    ``replacement`` is text, or a function. A function receives the
    matched pieces as one character vector and its return value is
    written over the first match. ``""`` and ``boundary()`` are rejected
    for text and accepted for a function, where ``""`` is a character
    boundary.
    """

    if _is_replacement_fun(replacement):
        return _transform_first(string, pattern, replacement)
    return _replace_text(string, pattern, replacement, False)


def str_replace_all(string, pattern, replacement=_MISSING):
    """Replace every match.

    A dict, or a vector with ``names``, is a sequence of pattern and
    replacement pairs applied to each string. ``replacement`` is then
    unused, which is why it can be left out. A function receives every
    match in one vector. Its return value has to be character and the
    same length; the pieces are put back with ``stri_sub_replace_all``.
    """

    if replacement is not _MISSING and _is_replacement_fun(replacement):
        return _transform_all(string, pattern, replacement)
    if replacement is _MISSING and _named_rewrite(pattern) is None:
        raise TypeError("`replacement` is missing, with no default")
    supplied = None if replacement is _MISSING else replacement
    return _replace_text(string, pattern, supplied, True)


def str_remove(string, pattern):
    """Remove the first match. This is ``str_replace`` with ``""``."""

    return str_replace(string, pattern, "")


def str_remove_all(string, pattern):
    """Remove every match. This is ``str_replace_all`` with ``""``."""

    return str_replace_all(string, pattern, "")


def str_replace_na(string, replacement="NA"):
    """Replace each missing character with ``replacement``.

    The default is the text ``"NA"``. ``replacement`` is one string.
    """

    repl = _check_string(replacement)
    if string is None:
        return []
    out = stri_replace_na(_coerce_character(string), repl)
    return _copy_names(string, out)


def _replace_text(string, pattern, replacement, replace_all: bool):
    named = _named_rewrite(pattern) if replace_all else None
    if named is not None:
        search, repl, kind, opts = named
        if string is None:
            _reject_bad_kind(kind)
            return []
        texts = _coerce_character(string)
        prepared = _prepare_replacement(kind, repl)
        out = _call_replace(kind, True, texts, search, prepared, opts, False)
        return _preserve(string, len(search), out)

    kind = _kind(pattern)
    check_lengths(string, pattern, replacement)
    _reject_bad_kind(kind)
    prepared = _prepare_replacement(kind, replacement)
    if string is None or prepared is None:
        return []
    texts = _coerce_character(string)
    search = _pattern_values(pattern)
    opts = pattern_opts(pattern)
    out = _call_replace(kind, replace_all, texts, search, prepared, opts, True)
    return _preserve(string, _vec_len(pattern), out)


def _prepare_replacement(kind: str, replacement):
    """Regex keeps character replacement and rewrites backslashes.

    Fixed and collation replacement is coerced, and ``NULL`` becomes an
    empty result. That empty result is ``None`` here.
    """

    if kind == "regex":
        return fix_replacement(replacement)
    if replacement is None:
        return None
    return _coerce_character(replacement)


def _reject_bad_kind(kind: str) -> None:
    if kind == "empty":
        no_empty()
    if kind == "bound":
        no_boundary()


def _call_replace(kind, replace_all, texts, search, replacement, opts, vectorize_all):
    if kind == "fixed":
        if replace_all:
            return stri_replace_all_fixed(
                texts, search, replacement, vectorize_all=vectorize_all, opts_fixed=opts
            )
        return stri_replace_first_fixed(texts, search, replacement, opts_fixed=opts)
    if kind == "coll":
        if replace_all:
            return stri_replace_all_coll(
                texts,
                search,
                replacement,
                vectorize_all=vectorize_all,
                opts_collator=opts,
            )
        return stri_replace_first_coll(texts, search, replacement, opts_collator=opts)
    if kind == "regex":
        if replace_all:
            return stri_replace_all_regex(
                texts, search, replacement, vectorize_all=vectorize_all, opts_regex=opts
            )
        return stri_replace_first_regex(texts, search, replacement, opts_regex=opts)
    _reject_bad_kind(kind)
    raise ValueError(f"`pattern` must be a character vector, not {kind}.")


def _transform_first(string, pattern, replacement):
    texts, locs = _locate(string, pattern, False)
    found = stri_sub(texts, from_=locs) if texts else []
    new = _coerce_character(replacement(found))
    if not texts and not new:
        return []
    return list(stri_sub_replace(texts, from_=locs, omit_na=True, value=new))


def _transform_all(string, pattern, replacement):
    texts, locs = _locate(string, pattern, True)
    if not texts:
        return []
    found = stri_sub_all(texts, from_=locs)
    flat = list_unchop(found)
    if len(flat) == 0:
        new_groups = [[] for _ in found]
    else:
        try:
            returned = replacement(flat)
        except Exception as exc:
            raise ValueError(
                "Failed to apply `replacement` function. "
                "It must accept a character vector of any length."
            ) from exc
        new_flat = _require_character(returned, len(flat))
        new_groups = _chop(new_flat, _chop_index(found))
    return list(stri_sub_replace_all(texts, from_=locs, value=new_groups))


def _locate(string, pattern, replace_all: bool):
    check_lengths(string, pattern)
    kind = _kind(pattern)
    opts = pattern_opts(pattern)
    texts = [] if string is None else _coerce_character(string)
    if not texts:
        rows = []
        return texts, rows
    values = _pattern_values(pattern)
    if kind in ("empty", "bound"):
        if replace_all:
            rows = stri_locate_all_boundaries(texts, omit_no_match=True, opts_brkiter=opts)
        else:
            rows = stri_locate_first_boundaries(texts, opts_brkiter=opts)
        return texts, rows
    if kind == "fixed":
        if replace_all:
            rows = stri_locate_all_fixed(
                texts, values, omit_no_match=True, opts_fixed=opts
            )
        else:
            rows = stri_locate_first_fixed(texts, values, opts_fixed=opts)
        return texts, rows
    if kind == "coll":
        if replace_all:
            rows = stri_locate_all_coll(
                texts, values, omit_no_match=True, opts_collator=opts
            )
        else:
            rows = stri_locate_first_coll(texts, values, opts_collator=opts)
        return texts, rows
    if kind == "regex":
        if replace_all:
            rows = stri_locate_all_regex(texts, values, omit_no_match=True, opts_regex=opts)
        else:
            rows = stri_locate_first_regex(texts, values, opts_regex=opts)
        return texts, rows
    raise ValueError("`pattern` must be a character vector.")


def _chop_index(groups):
    """1-based index ranges for each group, matching ``chop_index``.

    ``seq2`` is empty when the start is past the end, which is how a
    group of length 0 is skipped.
    """

    lengths = [len(group) for group in groups]
    if not lengths:
        return []
    running = 0
    starts = []
    for item in (1, *lengths[:-1]):
        running += item
        starts.append(running)
    indexes = []
    for start, size in zip(starts, lengths):
        end = start + size - 1
        if start > end:
            indexes.append([])
        else:
            indexes.append(list(range(start, end + 1)))
    return indexes


def _chop(flat, indexes):
    return [[flat[i - 1] for i in index] for index in indexes]


def fix_replacement(replacement):
    """Turn ``\\1`` into ``$1`` and escape ``$`` for ICU."""

    _check_character(replacement, "replacement")
    return [_fix_one(item) for item in _as_items(replacement)]


def _fix_one(text):
    if is_na(text):
        return NA
    out = []
    escaped = False
    for char in text:
        if escaped:
            if char == "$":
                out.append("\\\\$")
            elif "0" <= char <= "9":
                out.append("$" + char)
            else:
                out.append("\\" + char)
            escaped = False
        elif char == "$":
            out.append("\\$")
        elif char == "\\":
            escaped = True
        else:
            out.append(char)
    return "".join(out)


def _is_replacement_fun(value) -> bool:
    return callable(value) and not isinstance(value, type)


def _kind(pattern) -> str:
    try:
        return pattern_type(pattern)
    except TypeError as exc:
        raise ValueError(
            f"`pattern` must be a character vector, not {_friendly(pattern)}."
        ) from exc


def _pattern_values(pattern):
    if isinstance(pattern, Pattern) or isinstance(pattern, (list, tuple)):
        return list(pattern)
    if isinstance(pattern, str) or is_na(pattern):
        return [pattern]
    raise ValueError(f"`pattern` must be a character vector, not {_friendly(pattern)}.")


def _named_rewrite(pattern):
    """A named vector's names are the patterns and its values the replacements.

    After that rewrite a plain character vector still has names, so it is
    not the empty pattern even when a name is ``""``. A modifier keeps
    its own kind and options.
    """

    if isinstance(pattern, dict):
        search = [_name_string(key) for key in pattern]
        if any(is_na(item) for item in search):
            raise ValueError("pattern can not contain NAs.")
        return search, list(pattern.values()), "regex", None
    names = getattr(pattern, "names", None)
    if names is None:
        return None
    values = list(pattern) if isinstance(pattern, (list, tuple)) else [pattern]
    search = [_name_string(name) for name in names]
    if len(search) != len(values):
        raise ValueError("`pattern` names must have the same length as `pattern`.")
    if isinstance(pattern, Pattern):
        return search, values, pattern_type(pattern), pattern_opts(pattern)
    if any(is_na(item) for item in search):
        raise ValueError("pattern can not contain NAs.")
    return search, values, "regex", None


def _name_string(name):
    if name is None or is_na(name):
        return NA
    if isinstance(name, str):
        return name
    return _one_character(name)


def _preserve(string, pattern_length, out):
    values = list(out)
    if pattern_length == 1 or pattern_length == _vec_len(string):
        return _copy_names(string, values)
    return values


def _copy_names(string, out):
    names = getattr(string, "names", None)
    if names is None:
        return list(out)
    names = list(names)
    if len(out) == len(names):
        return _Named(out, names)
    if len(names) == 1 and len(out) > 1:
        return _Named(out, names * len(out))
    if len(out) == 0:
        return []
    raise ValueError("`names` must match the length of the result.")


def _check_string(replacement) -> str:
    if is_na(replacement) or (
        isinstance(replacement, (list, tuple))
        and len(replacement) == 1
        and is_na(replacement[0])
    ):
        raise ValueError("`replacement` must be a single string, not `NA`.")
    if isinstance(replacement, str):
        return replacement
    if (
        isinstance(replacement, (list, tuple))
        and len(replacement) == 1
        and isinstance(replacement[0], str)
    ):
        return replacement[0]
    if isinstance(replacement, (list, tuple)) and _is_character(replacement):
        raise ValueError("`replacement` must be a single string, not a character vector.")
    raise ValueError(
        f"`replacement` must be a single string, not {_friendly(replacement)}."
    )


def _check_character(value, arg: str) -> None:
    if _is_character(value):
        return
    raise ValueError(f"`{arg}` must be a character vector, not {_friendly(value)}.")


def _is_character(value) -> bool:
    if isinstance(value, str) or is_na(value):
        return True
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, str) or is_na(item) for item in value)
    return False


def _require_character(value, expected: int):
    if isinstance(value, str) or is_na(value):
        got = [value]
    elif isinstance(value, (list, tuple)) and _is_character(value):
        got = list(value)
    else:
        raise ValueError(
            "`replacement` function must return a character vector, "
            f"not {_return_friendly(value)}."
        )
    if len(got) != expected:
        raise ValueError(
            "`replacement` function must return a vector the same length as "
            f"the input ({expected}), not length {len(got)}."
        )
    return got


def _as_items(value):
    if isinstance(value, str) or is_na(value):
        return [value]
    return list(value)


def _coerce_character(value):
    if isinstance(value, str) or is_na(value):
        return [value]
    if isinstance(value, (list, tuple)):
        return [_one_character(item) for item in value]
    return [_one_character(value)]


def _one_character(value):
    if is_na(value):
        return NA
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _character_double(value)
    raise TypeError(
        "argument should be a character vector (or an integer, logical, or missing value)"
    )


def _character_double(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    if value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return str(value)


def _return_friendly(value) -> str:
    if isinstance(value, bool):
        return "`TRUE`" if value else "`FALSE`"
    if isinstance(value, (int, float)):
        return "a number"
    if value is None:
        return "`NULL`"
    if isinstance(value, (list, tuple)):
        return "a list"
    return _friendly(value)


def _friendly(value) -> str:
    if value is None:
        return "`NULL`"
    if isinstance(value, bool):
        return "`TRUE`" if value else "`FALSE`"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"the number {value}"
    if isinstance(value, str) or is_na(value):
        return "a string"
    if callable(value):
        return "a function"
    if isinstance(value, (list, tuple)):
        return "a list"
    return f"a {type(value).__name__}"


def _vec_len(value) -> int:
    if value is None:
        return 0
    if is_na(value) or isinstance(value, (str, bool, int, float)):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1
