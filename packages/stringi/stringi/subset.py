"""Subset replacement from stringi 1.8.9.

``stri_subset_assign`` is R's ``stri_subset<-``. The mode-specific
functions are ``stri_subset_fixed<-``, ``stri_subset_coll<-``,
``stri_subset_regex<-``, and ``stri_subset_charclass<-``.

Each call returns a new list the same length as ``str``. The caller's
list is left unchanged. A match is overwritten by the next element of
``value``; ``value`` is recycled over the matches, not over ``str``.
A missing pattern keeps the original string. An empty fixed, regex, or
collation pattern makes that element missing. Search itself is the
already translated ``stri_subset_*`` function.
"""

from __future__ import annotations

import math
import warnings

from stringi._na import NA, is_na
from stringi.charclass import stri_subset_charclass
from stringi.coll import stri_subset_coll
from stringi.fixed import stri_subset_fixed
from stringi.length import _prepare
from stringi.opts import _r_deparse, stri_opts_collator, stri_opts_fixed, stri_opts_regex
from stringi.regex import stri_subset_regex

_MISSING = object()


def _strings(value, name: str) -> list:
    """Coerce the way ``stri__prepare_arg_string`` does.

    ``None`` is R's ``NULL``, an empty character vector. A missing
    character inside a vector is :data:`stringi._na.NA`.
    """

    try:
        texts, _scalar = _prepare(value)
    except TypeError as exc:
        if "not None" in str(exc):
            raise
        raise ValueError(
            f"argument `{name}` should be a character vector (or an object coercible to)"
        ) from None
    return texts


def _negate(value) -> bool:
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument `negate` should be a non-empty vector")
        if len(value) > 1:
            warnings.warn(
                "argument `negate` should be a single logical value; "
                "only the first element is used",
                stacklevel=3,
            )
        value = value[0]
    if value is None:
        raise ValueError("argument `negate` should be a non-empty vector")
    if is_na(value) or (isinstance(value, float) and math.isnan(value)):
        raise ValueError("missing values in argument `negate` is not supported")
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float):
        if math.isinf(value):
            raise ValueError("missing values in argument `negate` is not supported")
        return value != 0
    raise TypeError("argument `negate` should be a single logical value")


def _unused(kwargs: dict) -> None:
    parts = [f"{key} = {_r_deparse(val)}" for key, val in kwargs.items()]
    label = "argument" if len(parts) == 1 else "arguments"
    raise TypeError(f"unused {label} ({', '.join(parts)})")


def _merge(opts, kwargs: dict, builder, bad_message: str):
    """R's ``do.call(stri_opts_*, as.list(c(opts, ...)))`` when dots are used."""

    if not kwargs:
        return opts
    if opts is None:
        base: dict = {}
    elif isinstance(opts, dict):
        base = dict(opts)
    else:
        raise ValueError(bad_message)
    for key in kwargs:
        if key in base:
            raise TypeError(
                f'formal argument "{key}" matched by multiple actual arguments'
            )
    return builder(**{**base, **kwargs})


def _require_dict(opts, message: str) -> None:
    if opts is None or isinstance(opts, dict):
        return
    raise ValueError(message)


def _missing_pattern(pattern) -> None:
    if pattern is _MISSING:
        raise ValueError('argument "pattern" is missing, with no default')


def _missing_value(value) -> None:
    if value is _MISSING:
        raise ValueError('argument "value" is missing, with no default')


def _check_lengths(texts: list, patterns: list, values: list):
    if len(values) == 0:
        raise ValueError("replacement has length zero")
    if len(patterns) == 0:
        raise ValueError("vector has length zero")
    if len(texts) == 0:
        return []
    if len(texts) < len(patterns):
        raise ValueError("vector length not consistent with other arguments")
    if len(texts) % len(patterns) != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            stacklevel=3,
        )
    return None


def _probe(subset_fn, opt_name: str, opts) -> None:
    """Read options once, so a bad setting warns once."""

    if not isinstance(opts, dict) or not opts:
        return
    subset_fn("a", "a", omit_na=False, negate=False, **{opt_name: opts})


def _decide(subset_fn, text, pattern, negate: bool, opt_name, opts, cache: dict) -> str:
    """``keep`` the string, write ``NA``, or ``replace`` it.

    A missing pattern keeps the string. That is not what ``stri_subset_*``
    reports, so it is decided here. Every other decision is one call of
    the translated subset function.
    """

    if is_na(pattern):
        return "keep"
    key = (text, pattern)
    cached = cache.get(key)
    if cached is not None:
        return cached
    kwargs = {"omit_na": False, "negate": negate}
    if opt_name is not None and opts is not None:
        kwargs[opt_name] = opts
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        kept = subset_fn([text], pattern, **kwargs)
    if not kept:
        decision = "keep"
    elif is_na(kept[0]):
        decision = "na"
    else:
        decision = "replace"
    cache[key] = decision
    return decision


def _apply(subset_fn, texts, patterns, values, negate, opt_name, opts, blank_is_na: bool):
    if blank_is_na:
        for pattern in patterns:
            if not is_na(pattern) and pattern == "":
                warnings.warn(
                    "empty search patterns are not supported",
                    stacklevel=3,
                )
    cache: dict = {}
    out = []
    matched = 0
    n_patterns = len(patterns)
    n_values = len(values)
    for index, text in enumerate(texts):
        pattern = patterns[index % n_patterns]
        if blank_is_na and not is_na(pattern) and pattern == "":
            out.append(NA)
            continue
        decision = _decide(subset_fn, text, pattern, negate, opt_name, opts, cache)
        if decision == "na":
            out.append(NA)
        elif decision == "replace":
            out.append(values[matched % n_values])
            matched += 1
        else:
            out.append(text)
    if matched % n_values != 0:
        warnings.warn(
            "number of items to replace is not a multiple of replacement length",
            stacklevel=3,
        )
    return out


def stri_subset_fixed_assign(
    str,
    pattern=_MISSING,
    negate=False,
    *,
    value=_MISSING,
    opts_fixed=None,
    **kwargs,
):
    """Replace strings that contain a literal pattern. This is ``stri_subset_fixed<-``.

    ``value`` is recycled over the matches. A missing pattern keeps the
    string. An empty pattern makes that element ``NA`` and warns.
    ``overlap`` is ignored. The result is a new list.
    """

    opts = _merge(
        opts_fixed,
        kwargs,
        stri_opts_fixed,
        "argument `opts_fixed` should be a list",
    )
    _missing_pattern(pattern)
    _missing_value(value)
    neg = _negate(negate)
    _require_dict(opts, "argument `opts_fixed` should be a list")
    _probe(stri_subset_fixed, "opts_fixed", opts)
    texts = _strings(str, "str")
    patterns = _strings(pattern, "pattern")
    values = _strings(value, "value")
    early = _check_lengths(texts, patterns, values)
    if early is not None:
        return early
    return _apply(stri_subset_fixed, texts, patterns, values, neg, "opts_fixed", opts, True)


def stri_subset_regex_assign(
    str,
    pattern=_MISSING,
    negate=False,
    *,
    value=_MISSING,
    opts_regex=None,
    **kwargs,
):
    """Replace strings that match a regular expression. This is ``stri_subset_regex<-``.

    An empty string is searched. An empty pattern makes that element
    ``NA`` and warns. A missing pattern keeps the string. The result is
    a new list.
    """

    opts = _merge(
        opts_regex,
        kwargs,
        stri_opts_regex,
        "argument `opts_regex` should be a list",
    )
    _missing_pattern(pattern)
    _missing_value(value)
    neg = _negate(negate)
    texts = _strings(str, "str")
    patterns = _strings(pattern, "pattern")
    values = _strings(value, "value")
    early = _check_lengths(texts, patterns, values)
    if early is not None:
        return early
    _require_dict(opts, "argument `opts_regex` should be a list")
    _probe(stri_subset_regex, "opts_regex", opts)
    return _apply(stri_subset_regex, texts, patterns, values, neg, "opts_regex", opts, True)


def stri_subset_coll_assign(
    str,
    pattern=_MISSING,
    negate=False,
    *,
    value=_MISSING,
    opts_collator=None,
    **kwargs,
):
    """Replace strings that contain a collation pattern. This is ``stri_subset_coll<-``.

    An empty string follows ``negate`` and is not searched. An empty
    pattern makes that element ``NA`` and warns. A missing pattern keeps
    the string. The result is a new list.
    """

    opts = _merge(
        opts_collator,
        kwargs,
        stri_opts_collator,
        "incorrect collator option specifier, see ?stri_opts_collator",
    )
    _missing_pattern(pattern)
    _missing_value(value)
    neg = _negate(negate)
    texts = _strings(str, "str")
    patterns = _strings(pattern, "pattern")
    values = _strings(value, "value")
    early = _check_lengths(texts, patterns, values)
    if early is not None:
        return early
    _require_dict(opts, "incorrect collator option specifier, see ?stri_opts_collator")
    _probe(stri_subset_coll, "opts_collator", opts)
    return _apply(stri_subset_coll, texts, patterns, values, neg, "opts_collator", opts, True)


def stri_subset_charclass_assign(
    str,
    pattern=_MISSING,
    negate=False,
    *,
    value=_MISSING,
    **kwargs,
):
    """Replace strings that contain a character class. This is ``stri_subset_charclass<-``.

    An empty string follows ``negate``. A missing pattern keeps the
    string. An empty pattern is an invalid UnicodeSet. The result is a
    new list.
    """

    if kwargs:
        _unused(kwargs)
    _missing_pattern(pattern)
    _missing_value(value)
    neg = _negate(negate)
    texts = _strings(str, "str")
    patterns = _strings(pattern, "pattern")
    values = _strings(value, "value")
    early = _check_lengths(texts, patterns, values)
    if early is not None:
        return early
    return _apply(
        stri_subset_charclass, texts, patterns, values, neg, None, None, False
    )


def stri_subset_assign(
    str,
    *,
    value=_MISSING,
    regex=_MISSING,
    fixed=_MISSING,
    coll=_MISSING,
    charclass=_MISSING,
    **kwargs,
):
    """Replace strings selected by exactly one search engine. This is ``stri_subset<-``.

    Pass one of ``regex``, ``fixed``, ``coll``, or ``charclass``. ``None``
    is R's ``NULL`` and counts as supplied. Omitting the argument does not.
    """

    supplied = []
    if regex is not _MISSING:
        supplied.append((regex, stri_subset_regex_assign))
    if fixed is not _MISSING:
        supplied.append((fixed, stri_subset_fixed_assign))
    if coll is not _MISSING:
        supplied.append((coll, stri_subset_coll_assign))
    if charclass is not _MISSING:
        supplied.append((charclass, stri_subset_charclass_assign))
    if len(supplied) != 1:
        raise ValueError(
            "you have to specify either `regex`, `fixed`, `coll`, or `charclass`"
        )
    pattern, function = supplied[0]
    return function(str, pattern, value=value, **kwargs)
