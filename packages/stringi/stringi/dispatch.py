"""Search dispatchers for stringi 1.8.9.

Each function only chooses a finished mode function. It does not search.
Exactly one of ``regex``, ``fixed``, ``coll``, and ``charclass`` must be
supplied. An omitted argument is not :data:`None`: ``None`` is an explicit
``NULL`` and is a supplied empty pattern. Zero or two or more of those
arguments is an error. Names that follow ``...`` are not partially matched,
so ``reg`` does not select ``regex``.

``stri_extract``, ``stri_locate``, and ``stri_replace`` take ``mode``.
``match.arg`` accepts a unique prefix. A missing mode and ``mode=NULL``
are ``first``. ``stri_startswith`` and ``stri_endswith`` have no regex
argument.

Extra keyword arguments are forwarded. The mode functions already accept
the ``opts_*`` settings as keywords.
"""

from __future__ import annotations

from stringi._na import is_na
from stringi.charclass import (
    stri_count_charclass,
    stri_detect_charclass,
    stri_endswith_charclass,
    stri_extract_all_charclass,
    stri_extract_first_charclass,
    stri_extract_last_charclass,
    stri_locate_all_charclass,
    stri_locate_first_charclass,
    stri_locate_last_charclass,
    stri_replace_all_charclass,
    stri_replace_first_charclass,
    stri_replace_last_charclass,
    stri_split_charclass,
    stri_startswith_charclass,
    stri_subset_charclass,
)
from stringi.coll import (
    stri_count_coll,
    stri_detect_coll,
    stri_endswith_coll,
    stri_extract_all_coll,
    stri_extract_first_coll,
    stri_extract_last_coll,
    stri_locate_all_coll,
    stri_locate_first_coll,
    stri_locate_last_coll,
    stri_replace_all_coll,
    stri_replace_first_coll,
    stri_replace_last_coll,
    stri_split_coll,
    stri_startswith_coll,
    stri_subset_coll,
)
from stringi.fixed import (
    stri_count_fixed,
    stri_detect_fixed,
    stri_endswith_fixed,
    stri_extract_all_fixed,
    stri_extract_first_fixed,
    stri_extract_last_fixed,
    stri_locate_all_fixed,
    stri_locate_first_fixed,
    stri_locate_last_fixed,
    stri_replace_all_fixed,
    stri_replace_first_fixed,
    stri_replace_last_fixed,
    stri_split_fixed,
    stri_startswith_fixed,
    stri_subset_fixed,
)
from stringi.regex import (
    stri_count_regex,
    stri_detect_regex,
    stri_extract_all_regex,
    stri_extract_first_regex,
    stri_extract_last_regex,
    stri_locate_all_regex,
    stri_locate_first_regex,
    stri_locate_last_regex,
    stri_replace_all_regex,
    stri_replace_first_regex,
    stri_replace_last_regex,
    stri_split_regex,
    stri_subset_regex,
)

_MISSING = object()

_NEED_ONE = "you have to specify either `regex`, `fixed`, `coll`, or `charclass`"
_NEED_ONE_OF = "you have to specify one of: `regex`, `fixed`, `coll`, or `charclass`"
_NEED_EDGE = "you have to specify either `fixed`, `coll`, or `charclass`"
_REPLACEMENT = 'argument "replacement" is missing, with no default'

_MODES = ("first", "all", "last")
_MODE_SHOULD = "'arg' should be one of \u201cfirst\u201d, \u201call\u201d, \u201clast\u201d"
_MODE_LENGTH = "'arg' must be of length 1"
_MODE_TYPE = "'arg' must be NULL or a character vector"
_MODE_MANY = "there is more than one match in 'match.arg'"

_COUNT = {
    "regex": stri_count_regex,
    "fixed": stri_count_fixed,
    "coll": stri_count_coll,
    "charclass": stri_count_charclass,
}
_DETECT = {
    "regex": stri_detect_regex,
    "fixed": stri_detect_fixed,
    "coll": stri_detect_coll,
    "charclass": stri_detect_charclass,
}
_EXTRACT_ALL = {
    "regex": stri_extract_all_regex,
    "fixed": stri_extract_all_fixed,
    "coll": stri_extract_all_coll,
    "charclass": stri_extract_all_charclass,
}
_EXTRACT_FIRST = {
    "regex": stri_extract_first_regex,
    "fixed": stri_extract_first_fixed,
    "coll": stri_extract_first_coll,
    "charclass": stri_extract_first_charclass,
}
_EXTRACT_LAST = {
    "regex": stri_extract_last_regex,
    "fixed": stri_extract_last_fixed,
    "coll": stri_extract_last_coll,
    "charclass": stri_extract_last_charclass,
}
_LOCATE_ALL = {
    "regex": stri_locate_all_regex,
    "fixed": stri_locate_all_fixed,
    "coll": stri_locate_all_coll,
    "charclass": stri_locate_all_charclass,
}
_LOCATE_FIRST = {
    "regex": stri_locate_first_regex,
    "fixed": stri_locate_first_fixed,
    "coll": stri_locate_first_coll,
    "charclass": stri_locate_first_charclass,
}
_LOCATE_LAST = {
    "regex": stri_locate_last_regex,
    "fixed": stri_locate_last_fixed,
    "coll": stri_locate_last_coll,
    "charclass": stri_locate_last_charclass,
}
_REPLACE_ALL = {
    "regex": stri_replace_all_regex,
    "fixed": stri_replace_all_fixed,
    "coll": stri_replace_all_coll,
    "charclass": stri_replace_all_charclass,
}
_REPLACE_FIRST = {
    "regex": stri_replace_first_regex,
    "fixed": stri_replace_first_fixed,
    "coll": stri_replace_first_coll,
    "charclass": stri_replace_first_charclass,
}
_REPLACE_LAST = {
    "regex": stri_replace_last_regex,
    "fixed": stri_replace_last_fixed,
    "coll": stri_replace_last_coll,
    "charclass": stri_replace_last_charclass,
}
_SPLIT = {
    "regex": stri_split_regex,
    "fixed": stri_split_fixed,
    "coll": stri_split_coll,
    "charclass": stri_split_charclass,
}
_START = {
    "fixed": stri_startswith_fixed,
    "coll": stri_startswith_coll,
    "charclass": stri_startswith_charclass,
}
_END = {
    "fixed": stri_endswith_fixed,
    "coll": stri_endswith_coll,
    "charclass": stri_endswith_charclass,
}
_SUBSET = {
    "regex": stri_subset_regex,
    "fixed": stri_subset_fixed,
    "coll": stri_subset_coll,
    "charclass": stri_subset_charclass,
}


def _pattern(value):
    """R ``NULL`` is an empty character vector for these pattern arguments."""
    if value is None:
        return []
    return value


def _choose(pairs: tuple[tuple[str, object], ...], message: str) -> tuple[str, object]:
    found = [(name, value) for name, value in pairs if value is not _MISSING]
    if len(found) != 1:
        raise ValueError(message)
    return found[0]


def _four(regex, fixed, coll, charclass) -> tuple[tuple[str, object], ...]:
    return (
        ("regex", regex),
        ("fixed", fixed),
        ("coll", coll),
        ("charclass", charclass),
    )


def _three(fixed, coll, charclass) -> tuple[tuple[str, object], ...]:
    return (("fixed", fixed), ("coll", coll), ("charclass", charclass))


def _invoke(functions, name, pattern, str, args, kwargs, replacement=_MISSING):
    fn = functions[name]
    pattern = _pattern(pattern)
    if replacement is _MISSING:
        return fn(str, pattern, *args, **kwargs)
    return fn(str, pattern, _pattern(replacement), *args, **kwargs)


def _search(functions, str, args, pairs, kwargs, message):
    name, pattern = _choose(pairs, message)
    return _invoke(functions, name, pattern, str, args, kwargs)


def _replace(functions, str, replacement, args, pairs, kwargs, message):
    name, pattern = _choose(pairs, message)
    if replacement is _MISSING:
        raise ValueError(_REPLACEMENT)
    return _invoke(functions, name, pattern, str, args, kwargs, replacement)


def _match_mode(mode) -> str:
    """R ``match.arg`` for ``c("first", "all", "last")``."""
    if mode is _MISSING or mode is None:
        return "first"
    if is_na(mode):
        raise ValueError(_MODE_SHOULD)
    if isinstance(mode, str):
        values = [mode]
    elif isinstance(mode, (list, tuple)):
        values = list(mode)
    else:
        raise ValueError(_MODE_TYPE)
    if values == ["first", "all", "last"]:
        return "first"
    if any(not isinstance(item, str) and not is_na(item) for item in values):
        raise ValueError(_MODE_TYPE)
    if len(values) != 1:
        raise ValueError(_MODE_LENGTH)
    arg = values[0]
    if is_na(arg) or arg == "":
        raise ValueError(_MODE_SHOULD)
    exact = [choice for choice in _MODES if choice == arg]
    hits = exact or [choice for choice in _MODES if choice.startswith(arg)]
    if not hits:
        raise ValueError(_MODE_SHOULD)
    if len(hits) > 1:
        raise ValueError(_MODE_MANY)
    return hits[0]


def stri_count(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Count matches using regex, fixed, coll, or charclass.

    Exactly one pattern argument is required. Further keywords, such as
    ``case_insensitive`` or ``strength``, are passed to that mode function.
    """
    return _search(_COUNT, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_detect(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Report matches using regex, fixed, coll, or charclass.

    Exactly one pattern argument is required. ``negate`` and ``max_count``
    are forwarded.
    """
    return _search(_DETECT, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE_OF)


def stri_extract_all(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Extract every match using regex, fixed, coll, or charclass."""
    return _search(_EXTRACT_ALL, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_extract_first(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Extract the first match using regex, fixed, coll, or charclass."""
    return _search(_EXTRACT_FIRST, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_extract_last(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Extract the last match using regex, fixed, coll, or charclass."""
    return _search(_EXTRACT_LAST, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_extract(
    str,
    *args,
    regex=_MISSING,
    fixed=_MISSING,
    coll=_MISSING,
    charclass=_MISSING,
    mode=_MISSING,
    **kwargs,
):
    """Extract matches in the mode ``first`` (the default), ``all``, or ``last``.

    ``mode`` is resolved before the pattern arguments are checked. ``NULL``
    and a missing mode are ``first``. A unique prefix such as ``"a"`` is
    ``all``.
    """
    chosen = _match_mode(mode)
    target = {"first": stri_extract_first, "all": stri_extract_all, "last": stri_extract_last}[chosen]
    return target(
        str,
        *args,
        regex=regex,
        fixed=fixed,
        coll=coll,
        charclass=charclass,
        **kwargs,
    )


def stri_locate_all(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Locate every match using regex, fixed, coll, or charclass."""
    return _search(_LOCATE_ALL, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_locate_first(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Locate the first match using regex, fixed, coll, or charclass."""
    return _search(_LOCATE_FIRST, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_locate_last(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Locate the last match using regex, fixed, coll, or charclass."""
    return _search(_LOCATE_LAST, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_locate(
    str,
    *args,
    regex=_MISSING,
    fixed=_MISSING,
    coll=_MISSING,
    charclass=_MISSING,
    mode=_MISSING,
    **kwargs,
):
    """Locate matches in the mode ``first`` (the default), ``all``, or ``last``.

    ``mode`` is resolved before the pattern arguments are checked.
    """
    chosen = _match_mode(mode)
    target = {"first": stri_locate_first, "all": stri_locate_all, "last": stri_locate_last}[chosen]
    return target(
        str,
        *args,
        regex=regex,
        fixed=fixed,
        coll=coll,
        charclass=charclass,
        **kwargs,
    )


def stri_replace_all(
    str,
    replacement=_MISSING,
    *args,
    regex=_MISSING,
    fixed=_MISSING,
    coll=_MISSING,
    charclass=_MISSING,
    **kwargs,
):
    """Replace every match using regex, fixed, coll, or charclass."""
    return _replace(_REPLACE_ALL, str, replacement, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_replace_first(
    str,
    replacement=_MISSING,
    *args,
    regex=_MISSING,
    fixed=_MISSING,
    coll=_MISSING,
    charclass=_MISSING,
    **kwargs,
):
    """Replace the first match using regex, fixed, coll, or charclass."""
    return _replace(
        _REPLACE_FIRST, str, replacement, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE
    )


def stri_replace_last(
    str,
    replacement=_MISSING,
    *args,
    regex=_MISSING,
    fixed=_MISSING,
    coll=_MISSING,
    charclass=_MISSING,
    **kwargs,
):
    """Replace the last match using regex, fixed, coll, or charclass."""
    return _replace(_REPLACE_LAST, str, replacement, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_replace(
    str,
    replacement=_MISSING,
    *args,
    regex=_MISSING,
    fixed=_MISSING,
    coll=_MISSING,
    charclass=_MISSING,
    mode=_MISSING,
    **kwargs,
):
    """Replace matches in the mode ``first`` (the default), ``all``, or ``last``.

    ``mode`` is resolved before the pattern arguments. A missing replacement
    is reported only after one pattern argument has been accepted.
    """
    chosen = _match_mode(mode)
    target = {"first": stri_replace_first, "all": stri_replace_all, "last": stri_replace_last}[chosen]
    return target(
        str,
        replacement,
        *args,
        regex=regex,
        fixed=fixed,
        coll=coll,
        charclass=charclass,
        **kwargs,
    )


def stri_split(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Split on regex, fixed, coll, or charclass.

    ``n``, ``omit_empty``, ``tokens_only``, and ``simplify`` are forwarded.
    """
    return _search(_SPLIT, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)


def stri_startswith(str, *args, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Report a match at ``from_`` using fixed, coll, or charclass.

    There is no regex argument. ``from_`` is R's ``from``.
    """
    return _search(_START, str, args, _three(fixed, coll, charclass), kwargs, _NEED_EDGE)


def stri_endswith(str, *args, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Report a match at ``to`` using fixed, coll, or charclass.

    There is no regex argument.
    """
    return _search(_END, str, args, _three(fixed, coll, charclass), kwargs, _NEED_EDGE)


def stri_subset(str, *args, regex=_MISSING, fixed=_MISSING, coll=_MISSING, charclass=_MISSING, **kwargs):
    """Keep the strings that match regex, fixed, coll, or charclass.

    ``omit_na`` and ``negate`` are forwarded.
    """
    return _search(_SUBSET, str, args, _four(regex, fixed, coll, charclass), kwargs, _NEED_ONE)
