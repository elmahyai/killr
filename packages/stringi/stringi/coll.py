"""Collation search from stringi 1.8.9.

Patterns are matched with ICU ``StringSearch`` and a ``Collator``. A match is a
contiguous piece of the original string. Its length in code points need not
equal the pattern length: at primary strength in German, ``ss`` matches one
``ß``. The next search starts after that match. ICU's overlap attribute stays
off, which is what the installed collators do; there is no ``overlap`` setting.

Missing character values are :data:`stringi._na.NA`. The string ``"NA"`` is
text. Positions from the locate functions are 1-based inclusive code-point
indexes. ``from_`` is R's ``from``. ``opts_collator`` is a dict of only the
settings that were passed. The normalization setting is stored as
``normalization``.
"""

from __future__ import annotations

import warnings

import icu

from stringi._na import NA, is_na
from stringi.opts import stri_opts_collator

_INT_MAX = 2147483647
_DONE = icu.SearchIterator.DONE
_STRENGTH_LIMIT = 16  # UCOL_STRENGTH_LIMIT, the value after UCOL_IDENTICAL

_ICU_STATUS = {
    1: ("Illegal argument.", "U_ILLEGAL_ARGUMENT_ERROR"),
    16: ("Requested operation not supported in current context.", "U_UNSUPPORTED_ERROR"),
}

_KNOWN_OPTS = (
    "locale",
    "strength",
    "alternate_shifted",
    "french",
    "uppercase_first",
    "case_level",
    "normalization",
    "numeric",
)


def _reraise_icu(exc: icu.ICUError) -> None:
    code = exc.args[0] if exc.args else None
    text, name = _ICU_STATUS.get(code, (str(exc.args[1] if len(exc.args) > 1 else exc), f"U_ERROR_{code}"))
    raise RuntimeError(f"{text} ({name})") from exc


def _as_strings(value: object, name: str) -> list:
    if is_na(value) or isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            if is_na(item) or isinstance(item, str):
                out.append(item)
            else:
                raise TypeError(f"{name} must be a string or a list of strings")
        return out
    raise TypeError(f"{name} must be a string or a list of strings")


def _one_int(value: object, name: str) -> object:
    if is_na(value):
        return NA
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            warnings.warn(f"NAs introduced by coercion to integer ({name})", stacklevel=3)
            return NA
        return int(value)
    raise TypeError(f"{name} must be an integer")


def _as_ints(value: object, name: str) -> list:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        return [_one_int(item, name) for item in value]
    return [_one_int(value, name)]


def _one_logical(value: object, name: str, allow_na: bool) -> object:
    if is_na(value):
        if allow_na:
            return NA
        raise ValueError(f"missing value in argument {name} is not allowed")
    if isinstance(value, bool):
        return value
    raise TypeError(f"{name} must be a single logical value")


def _as_logicals(value: object, name: str) -> list:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        return [_one_logical(item, name, True) for item in value]
    return [_one_logical(value, name, True)]


def _recycle_size(lengths: list[int]) -> int:
    if any(n <= 0 for n in lengths):
        return 0
    longest = max(lengths)
    for n in lengths:
        if longest % n != 0:
            warnings.warn(
                "longer object length is not a multiple of shorter object length",
                stacklevel=4,
            )
            break
    return longest


def _warn_empty(patterns: list) -> None:
    for pattern in patterns:
        if not is_na(pattern) and pattern == "":
            warnings.warn("empty search patterns are not supported", stacklevel=4)


def _at(values: list, index: int):
    return values[index % len(values)]


def _pattern_order(pattern_length: int, size: int) -> list[int]:
    """Order used by stringi's pattern container, which matters for max_count."""
    if size <= 0 or pattern_length <= 0:
        return []
    order = []
    index = 0
    end_mark = size - 1 - (size % pattern_length)
    while True:
        order.append(index)
        if index == end_mark:
            return order
        index += pattern_length
        if index >= size:
            index = (index % pattern_length) + 1


def _missing_pattern(text, pattern) -> bool:
    return is_na(text) or is_na(pattern) or pattern == ""


def _start_index(n: int, from_value: int) -> int:
    if from_value >= 0:
        index = from_value - 1
        if index <= 0:
            return 0
        return index if index < n else n
    back = -from_value
    if back <= 0:
        return n
    return n - back if back < n else 0


def _end_index(n: int, to_value: int) -> int:
    if to_value >= 0:
        if to_value <= 0:
            return 0
        return to_value if to_value < n else n
    back = -to_value - 1
    if back <= 0:
        return n
    return n - back if back < n else 0


def _no_match_row(get_length: bool):
    if get_length:
        return [-1, -1]
    return [NA, NA]


def _list2matrix(columns_of_rows: list, fill, n_min: int) -> list:
    width = n_min
    for row in columns_of_rows:
        if len(row) > width:
            width = len(row)
    matrix = []
    for row in columns_of_rows:
        padded = list(row)
        if len(padded) < width:
            padded.extend([fill] * (width - len(padded)))
        matrix.append(padded)
    return matrix


def _first_stored(value: object, name: str, kind: str):
    """Keep the first element of a length>1 option, as the C++ preparer does."""
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            warnings.warn(
                f"argument `{name}` should be a single {kind} value; only the first element is used",
                stacklevel=4,
            )
        return value[0]
    return value


def _missing_setting(name: str) -> ValueError:
    return ValueError(f"missing values in argument `{name}` is not supported")


def _as_flag(value: object, name: str, allow_na: bool):
    value = _first_stored(value, name, "logical")
    if is_na(value):
        if allow_na:
            return NA
        raise _missing_setting(name)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            if allow_na:
                return NA
            raise _missing_setting(name)
        return value != 0
    raise TypeError(f"argument `{name}` should be a logical vector (or an object coercible to)")


def _as_setting_int(value: object, name: str) -> int:
    value = _first_stored(value, name, "integer")
    if is_na(value):
        raise _missing_setting(name)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise _missing_setting(name)
        return int(value)
    raise TypeError(f"argument `{name}` should be an integer vector (or an object coercible to)")


def _is_c_locale(name: str) -> bool:
    return bool(name) and name[0] in "Cc" and (len(name) == 1 or name[1] == ".")


def _prepare_locale(value: object) -> str | None:
    """Return an ICU locale name. None asks for the process default."""
    value = _first_stored(value, "locale", "character")
    if value is None:
        return None
    if is_na(value):
        raise _missing_setting("locale")
    if not isinstance(value, str):
        raise TypeError("argument `locale` should be a character vector (or an object coercible to)")
    canon = icu.Locale.createCanonical(value).getName().strip(" \t\r\n")
    if canon == "":
        if value.strip(" \t\r\n") == "":
            return None
        return "root"
    if _is_c_locale(canon):
        return "en_US_POSIX"
    if canon.startswith("@"):
        default = icu.Locale.getDefault().getName()
        if _is_c_locale(default):
            default = "en_US_POSIX"
        return default + canon
    return canon


def _merge_opts(opts_collator, kwargs: dict) -> dict:
    """Apply R's ``c(opts_collator, ...)`` then ``stri_opts_collator`` when dots are used.

    With no extra arguments the dict is passed through. Unknown names are
    ignored later. ``normalisation`` is not renamed on that path.
    """
    if not kwargs:
        if opts_collator is None:
            return {}
        if isinstance(opts_collator, dict):
            return dict(opts_collator)
        raise TypeError("incorrect collator option specifier, see ?stri_opts_collator")
    if opts_collator is None:
        return stri_opts_collator(**kwargs)
    if not isinstance(opts_collator, dict):
        raise TypeError("incorrect collator option specifier, see ?stri_opts_collator")
    shared = [key for key in kwargs if key in opts_collator]
    if shared:
        raise TypeError(f'formal argument "{shared[0]}" matched by multiple actual arguments')
    merged = dict(opts_collator)
    merged.update(kwargs)
    return stri_opts_collator(**merged)


def _open_collator(opts: dict) -> icu.Collator:
    locale_name = None
    if "locale" in opts:
        locale_name = _prepare_locale(opts["locale"])
    if locale_name is None:
        default = icu.Locale.getDefault().getName()
        collator = icu.Collator.createInstance(
            icu.Locale("en_US_POSIX") if _is_c_locale(default) else icu.Locale.getDefault()
        )
    else:
        collator = icu.Collator.createInstance(icu.Locale(locale_name))
        if locale_name != "root":
            valid = collator.getLocale(icu.ULocDataLocaleType.VALID_LOCALE).getName()
            if valid in ("", "root"):
                warnings.warn(
                    "A resource bundle lookup returned a result either from the root or the default locale.",
                    stacklevel=4,
                )
    for key in opts:
        if key not in _KNOWN_OPTS:
            warnings.warn(f"incorrect opts_collator setting: '{key}'; ignoring", stacklevel=4)
    try:
        if "strength" in opts:
            val = _as_setting_int(opts["strength"], "strength")
            if val < icu.Collator.PRIMARY + 1:
                val = icu.Collator.PRIMARY + 1
            elif val > _STRENGTH_LIMIT + 1:
                val = _STRENGTH_LIMIT + 1
            collator.setAttribute(icu.UCollAttribute.STRENGTH, val - 1)
        if "french" in opts:
            flag = _as_flag(opts["french"], "french", False)
            collator.setAttribute(
                icu.UCollAttribute.FRENCH_COLLATION,
                icu.UCollAttributeValue.ON if flag else icu.UCollAttributeValue.OFF,
            )
        if "alternate_shifted" in opts:
            flag = _as_flag(opts["alternate_shifted"], "alternate_shifted", False)
            collator.setAttribute(
                icu.UCollAttribute.ALTERNATE_HANDLING,
                icu.UCollAttributeValue.SHIFTED if flag else icu.UCollAttributeValue.NON_IGNORABLE,
            )
        if "uppercase_first" in opts:
            flag = _as_flag(opts["uppercase_first"], "uppercase_first", True)
            if is_na(flag):
                case_first = icu.UCollAttributeValue.OFF
            elif flag:
                case_first = icu.UCollAttributeValue.UPPER_FIRST
            else:
                case_first = icu.UCollAttributeValue.LOWER_FIRST
            collator.setAttribute(icu.UCollAttribute.CASE_FIRST, case_first)
        if "case_level" in opts:
            flag = _as_flag(opts["case_level"], "case_level", False)
            collator.setAttribute(
                icu.UCollAttribute.CASE_LEVEL,
                icu.UCollAttributeValue.ON if flag else icu.UCollAttributeValue.OFF,
            )
        if "normalization" in opts:
            flag = _as_flag(opts["normalization"], "normalization", False)
            collator.setAttribute(
                icu.UCollAttribute.NORMALIZATION_MODE,
                icu.UCollAttributeValue.ON if flag else icu.UCollAttributeValue.OFF,
            )
        if "numeric" in opts:
            flag = _as_flag(opts["numeric"], "numeric", False)
            collator.setAttribute(
                icu.UCollAttribute.NUMERIC_COLLATION,
                icu.UCollAttributeValue.ON if flag else icu.UCollAttributeValue.OFF,
            )
    except icu.ICUError as exc:
        _reraise_icu(exc)
    return collator


def _has_supplementary(text: str) -> bool:
    return any(ord(ch) > 0xFFFF for ch in text)


def _cp_index(text: str, utf16_index: int) -> int:
    units = 0
    for index, ch in enumerate(text):
        if units >= utf16_index:
            return index
        units += 2 if ord(ch) > 0xFFFF else 1
    return len(text)


def _to_cp_span(text: str, start_u16: int, length_u16: int, supplementary: bool) -> tuple[int, int]:
    """Return a code-point span ``[start, end)`` from a UTF-16 match."""
    if not supplementary:
        return start_u16, start_u16 + length_u16
    start = _cp_index(text, start_u16)
    end = _cp_index(text, start_u16 + length_u16)
    return start, end


def _search(collator: icu.Collator, text: str, pattern: str) -> icu.StringSearch:
    try:
        return icu.StringSearch(pattern, text, collator)
    except icu.ICUError as exc:
        _reraise_icu(exc)


def _forward(search: icu.StringSearch, first: bool) -> list[tuple[int, int]]:
    """UTF-16 ``(start, length)`` matches, advancing the way the installed function does."""
    if first:
        pos = search.first()
    else:
        pos = search.nextMatch()
    spans = []
    previous = -1
    while pos != _DONE:
        if pos <= previous:
            break
        spans.append((pos, search.getMatchedLength()))
        previous = pos
        pos = search.nextMatch()
    return spans


def _match_spans(collator, text: str, pattern: str, mode: str) -> list[tuple[int, int]]:
    """Code-point spans ``[start, end)`` for ``mode`` in first, last, all, next."""
    search = _search(collator, text, pattern)
    supplementary = _has_supplementary(text)
    if mode == "last":
        pos = search.last()
        if pos == _DONE:
            return []
        return [_to_cp_span(text, pos, search.getMatchedLength(), supplementary)]
    if mode == "first":
        pos = search.first()
        if pos == _DONE:
            return []
        return [_to_cp_span(text, pos, search.getMatchedLength(), supplementary)]
    raw = _forward(search, mode == "all")
    return [_to_cp_span(text, start, length, supplementary) for start, length in raw]


def _utf16_len(text: str) -> int:
    total = 0
    for ch in text:
        total += 2 if ord(ch) > 0xFFFF else 1
    return total


def stri_count_coll(str, pattern, opts_collator=None, **kwargs):
    """Count collation matches of ``pattern`` in each string.

    An empty pattern or a missing string or pattern is ``NA``. An empty string
    with a non-empty pattern counts as 0. Each match is consumed before the
    next search, so ``ss`` counts once in ``ßß`` per ``ß``.
    """
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if _missing_pattern(text, pat):
            out.append(NA)
        elif text == "":
            out.append(0)
        else:
            out.append(len(_match_spans(collator, text, pat, "next")))
    return out


def stri_detect_coll(
    str,
    pattern,
    negate=False,
    max_count=-1,
    opts_collator=None,
    **kwargs,
):
    """Report whether each string contains a collation pattern.

    ``max_count`` stops after that many results of interest. Later elements are
    ``NA``. The elements are not always visited from left to right when
    ``pattern`` is longer than one. An empty string follows ``negate``.
    """
    neg = bool(_one_logical(negate, "negate", False))
    limit = _one_int(max_count, "max_count")
    if is_na(limit):
        raise ValueError("missing value in argument max_count is not allowed")
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    out = [None] * size
    for i in _pattern_order(len(patterns), size):
        if limit == 0:
            out[i] = NA
            continue
        text = _at(texts, i)
        pat = _at(patterns, i)
        if _missing_pattern(text, pat):
            out[i] = NA
            continue
        if text == "":
            out[i] = neg
        else:
            found = bool(_match_spans(collator, text, pat, "first"))
            out[i] = (not found) if neg else found
        if limit > 0 and out[i] is True:
            limit -= 1
    return out


def stri_startswith_coll(
    str,
    pattern,
    from_=1,
    negate=False,
    opts_collator=None,
    **kwargs,
):
    """Report whether a collation pattern matches at ``from_``.

    ``from_`` is R's ``from``: a 1-based code-point index. Negative values
    count back from the end, and ``-1`` is the last code point. An empty
    pattern or a missing value is ``NA``. An empty string follows ``negate``.
    The match has to begin at ``from_``; a later hit does not count.
    """
    neg = bool(_one_logical(negate, "negate", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    origins = _as_ints(from_, "from")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns), len(origins)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        origin = _at(origins, i)
        if _missing_pattern(text, pat):
            out.append(NA)
        elif text == "":
            out.append(neg)
        elif is_na(origin):
            out.append(NA)
        else:
            index = _start_index(len(text), origin)
            if index >= len(text):
                out.append(neg)
            else:
                search = _search(collator, text[index:], pat)
                pos = search.first()
                matched = pos != _DONE and pos == 0
                out.append((not matched) if neg else matched)
    return out


def stri_endswith_coll(
    str,
    pattern,
    to=-1,
    negate=False,
    opts_collator=None,
    **kwargs,
):
    """Report whether a collation pattern ends at ``to``.

    ``to`` is a 1-based code-point index. ``-1`` is the end of the string.
    An empty pattern or a missing value is ``NA``. An empty string follows
    ``negate``. The last match in the prefix must end exactly at ``to``.
    """
    neg = bool(_one_logical(negate, "negate", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    ends = _as_ints(to, "to")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns), len(ends)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        end = _at(ends, i)
        if _missing_pattern(text, pat):
            out.append(NA)
        elif text == "":
            out.append(neg)
        elif is_na(end):
            out.append(NA)
        else:
            stop = _end_index(len(text), end)
            if stop <= 0:
                out.append(neg)
            else:
                prefix = text[:stop]
                search = _search(collator, prefix, pat)
                pos = search.last()
                matched = pos != _DONE and pos + search.getMatchedLength() == _utf16_len(prefix)
                out.append((not matched) if neg else matched)
    return out


def _extract_edge(str, pattern, opts_collator, kwargs, mode: str):
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if _missing_pattern(text, pat) or text == "":
            out.append(NA)
            continue
        spans = _match_spans(collator, text, pat, mode)
        if not spans:
            out.append(NA)
        else:
            start, end = spans[0]
            out.append(text[start:end])
    return out


def stri_extract_first_coll(str, pattern, opts_collator=None, **kwargs):
    """Return the first collation match in each string, or ``NA``."""
    return _extract_edge(str, pattern, opts_collator, kwargs, "first")


def stri_extract_last_coll(str, pattern, opts_collator=None, **kwargs):
    """Return the last collation match in each string, or ``NA``."""
    return _extract_edge(str, pattern, opts_collator, kwargs, "last")


def stri_extract_all_coll(
    str,
    pattern,
    simplify=False,
    omit_no_match=False,
    opts_collator=None,
    **kwargs,
):
    """Return every collation match.

    The default is a list of character vectors. A missing match is a one-element
    ``NA`` vector unless ``omit_no_match`` is true, in which case that vector is
    empty. ``simplify=True`` pads a character matrix with empty strings.
    ``simplify`` missing (the ``NA`` object) pads with ``NA``.
    """
    omit = bool(_one_logical(omit_no_match, "omit_no_match", False))
    simple = _one_logical(simplify, "simplify", True)
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    columns = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if _missing_pattern(text, pat):
            columns.append([NA])
            continue
        if text == "":
            columns.append([] if omit else [NA])
            continue
        spans = _match_spans(collator, text, pat, "all")
        if not spans:
            columns.append([] if omit else [NA])
        else:
            columns.append([text[start:end] for start, end in spans])
    if simple is False:
        return columns
    fill = NA if is_na(simple) else ""
    return _list2matrix(columns, fill, 0)


def _locate_edge(str, pattern, get_length, opts_collator, kwargs, mode: str):
    length_mode = bool(_one_logical(get_length, "get_length", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    rows = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if _missing_pattern(text, pat):
            rows.append([NA, NA])
            continue
        if text == "":
            rows.append(_no_match_row(length_mode))
            continue
        spans = _match_spans(collator, text, pat, mode)
        if not spans:
            rows.append(_no_match_row(length_mode))
            continue
        start, end = spans[0]
        start_1 = start + 1
        if length_mode:
            rows.append([start_1, end - start])
        else:
            rows.append([start_1, end])
    return rows


def stri_locate_first_coll(
    str,
    pattern,
    get_length=False,
    opts_collator=None,
    **kwargs,
):
    """Locate the first collation match.

    Each row is ``start``, ``end``. Both are 1-based and inclusive. A miss is
    ``NA``, ``NA``. With ``get_length=True`` the second column is the length,
    and a miss or an empty string is ``-1``, ``-1``. A missing string stays
    ``NA``.
    """
    return _locate_edge(str, pattern, get_length, opts_collator, kwargs, "first")


def stri_locate_last_coll(
    str,
    pattern,
    get_length=False,
    opts_collator=None,
    **kwargs,
):
    """Locate the rightmost collation match."""
    return _locate_edge(str, pattern, get_length, opts_collator, kwargs, "last")


def stri_locate_all_coll(
    str,
    pattern,
    omit_no_match=False,
    get_length=False,
    opts_collator=None,
    **kwargs,
):
    """Locate every collation match.

    The result is a list of matrices. Each matrix has columns ``start`` and
    ``end``, or ``start`` and ``length`` when ``get_length`` is true. A miss is
    one ``NA`` row unless ``omit_no_match`` is true, in which case the matrix
    has no rows. An empty string uses ``-1`` when ``get_length`` is true.
    """
    omit = bool(_one_logical(omit_no_match, "omit_no_match", False))
    length_mode = bool(_one_logical(get_length, "get_length", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    matrices = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if _missing_pattern(text, pat):
            matrices.append([[NA, NA]])
            continue
        if text == "":
            matrices.append([] if omit else [_no_match_row(length_mode)])
            continue
        spans = _match_spans(collator, text, pat, "all")
        if not spans:
            matrices.append([] if omit else [_no_match_row(length_mode)])
            continue
        rows = []
        for start, end in spans:
            start_1 = start + 1
            if length_mode:
                rows.append([start_1, end - start])
            else:
                rows.append([start_1, end])
        matrices.append(rows)
    return matrices


def _replace_spans(collator, text: str, pattern: str, replacement: str, mode: str):
    if mode == "all":
        spans = _match_spans(collator, text, pattern, "all")
    else:
        spans = _match_spans(collator, text, pattern, mode)
    if not spans:
        return text
    if is_na(replacement):
        return NA
    parts = []
    cursor = 0
    for start, end in spans:
        parts.append(text[cursor:start])
        parts.append(replacement)
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def _replace_vectorized(str, pattern, replacement, opts_collator, kwargs, mode: str):
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    replacements = _as_strings(replacement, "replacement")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns), len(replacements)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        repl = _at(replacements, i)
        if _missing_pattern(text, pat):
            out.append(NA)
        elif text == "":
            out.append("")
        else:
            out.append(_replace_spans(collator, text, pat, repl, mode))
    return out


def stri_replace_first_coll(str, pattern, replacement, opts_collator=None, **kwargs):
    """Replace the first collation match. A miss returns the original string."""
    return _replace_vectorized(str, pattern, replacement, opts_collator, kwargs, "first")


def stri_replace_last_coll(str, pattern, replacement, opts_collator=None, **kwargs):
    """Replace the rightmost collation match."""
    return _replace_vectorized(str, pattern, replacement, opts_collator, kwargs, "last")


def stri_replace_all_coll(
    str,
    pattern,
    replacement,
    vectorize_all=True,
    vectorise_all=None,
    opts_collator=None,
    **kwargs,
):
    """Replace collation matches.

    With ``vectorize_all=True`` (the default), ``str``, ``pattern``, and
    ``replacement`` are recycled together. With ``vectorize_all=False``, each
    pattern is applied to every string, in order. ``pattern`` must be at least
    as long as ``replacement``. ``vectorise_all``, when given, overrides
    ``vectorize_all``.
    """
    if vectorise_all is not None:
        vectorize_all = vectorise_all
    together = bool(_one_logical(vectorize_all, "vectorize_all", False))
    if together:
        return _replace_vectorized(str, pattern, replacement, opts_collator, kwargs, "all")
    texts = _as_strings(str, "str")
    if len(texts) == 0:
        return []
    patterns = _as_strings(pattern, "pattern")
    replacements = _as_strings(replacement, "replacement")
    if len(patterns) < len(replacements) or len(patterns) == 0 or len(replacements) == 0:
        raise ValueError("vector length not consistent with other arguments")
    if len(patterns) % len(replacements) != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            stacklevel=2,
        )
    opts = _merge_opts(opts_collator, kwargs)
    if len(patterns) == 1:
        return _replace_vectorized(texts, patterns, replacements, opts, {}, "all")
    collator = _open_collator(opts)
    _warn_empty(patterns)
    current = list(texts)
    repls = [replacements[i % len(replacements)] for i in range(len(patterns))]
    for pat, repl in zip(patterns, repls):
        if is_na(pat):
            return [NA] * len(current)
        if pat == "":
            warnings.warn("empty search patterns are not supported", stacklevel=2)
            return [NA] * len(current)
        for j, text in enumerate(current):
            if is_na(text) or text == "":
                continue
            current[j] = _replace_spans(collator, text, pat, repl, "all")
    return current


def _split_one(collator, text, pattern, n_value, omit_value, tokens_only: bool):
    if is_na(n_value):
        return [NA]
    if _missing_pattern(text, pattern):
        return [NA]
    if text == "":
        if is_na(omit_value):
            return [NA]
        if omit_value or n_value == 0:
            return []
        return [""]
    if n_value >= _INT_MAX - 1:
        raise ValueError("incorrect n argument; expected a smaller value")
    if n_value == 0:
        return []
    unlimited = n_value < 0
    limit = None if unlimited else n_value + (1 if tokens_only else 0)
    fields = [[0, 0]]
    taken = 1
    for start, stop in _match_spans(collator, text, pattern, "next"):
        if limit is not None and taken >= limit:
            break
        if omit_value is True and fields[-1][0] == start:
            fields[-1][0] = stop
        else:
            fields[-1][1] = start
            fields.append([stop, stop])
            taken += 1
    fields[-1][1] = len(text)
    if omit_value is True and fields[-1][0] == fields[-1][1]:
        fields.pop()
    if tokens_only and not unlimited:
        while len(fields) > n_value:
            fields.pop()
    pieces = []
    for start, stop in fields:
        if start == stop and is_na(omit_value):
            pieces.append(NA)
        else:
            pieces.append(text[start:stop])
    return pieces


def stri_split_coll(
    str,
    pattern,
    n=-1,
    omit_empty=False,
    tokens_only=False,
    simplify=False,
    opts_collator=None,
    **kwargs,
):
    """Split each string on a collation delimiter.

    ``n`` below 0 returns every piece. A positive ``n`` returns ``n-1`` pieces
    and the remainder, unless ``tokens_only`` is true, which keeps at most
    ``n`` whole pieces. ``omit_empty=True`` drops empty pieces.
    ``omit_empty`` equal to the missing value replaces them with ``NA``.
    ``simplify=True`` returns a character matrix padded with empty strings;
    the missing value pads with ``NA``. The width is at least the largest
    positive ``n``.
    """
    tokens = bool(_one_logical(tokens_only, "tokens_only", False))
    simple = _one_logical(simplify, "simplify", True)
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    counts = _as_ints(n, "n")
    empties = _as_logicals(omit_empty, "omit_empty")
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    size = _recycle_size([len(texts), len(patterns), len(counts), len(empties)])
    _warn_empty(patterns)
    columns = []
    for i in range(size):
        columns.append(
            _split_one(
                collator,
                _at(texts, i),
                _at(patterns, i),
                _at(counts, i),
                _at(empties, i),
                tokens,
            )
        )
    if simple is False:
        return columns
    n_min = 0
    for count in counts:
        if not is_na(count) and n_min < count:
            n_min = count
    fill = NA if is_na(simple) else ""
    return _list2matrix(columns, fill, n_min)


def stri_subset_coll(
    str,
    pattern,
    omit_na=False,
    negate=False,
    opts_collator=None,
    **kwargs,
):
    """Keep the strings that contain a collation pattern.

    ``pattern`` cannot be longer than ``str`` when ``str`` is not empty.
    A missing string or an empty pattern is kept as ``NA`` unless ``omit_na``
    is true. ``negate`` keeps the strings that do not match. An empty string
    follows ``negate``.
    """
    neg = bool(_one_logical(negate, "negate", False))
    drop_na = bool(_one_logical(omit_na, "omit_na", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    if len(texts) > 0 and len(texts) < len(patterns):
        raise ValueError("vector length not consistent with other arguments")
    size = _recycle_size([len(texts), len(patterns)])
    if size == 0:
        return []
    opts = _merge_opts(opts_collator, kwargs)
    collator = _open_collator(opts)
    _warn_empty(patterns)
    chosen = [False] * size
    for i in _pattern_order(len(patterns), size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if _missing_pattern(text, pat):
            chosen[i] = False if drop_na else NA
            continue
        if text == "":
            chosen[i] = neg
            continue
        found = bool(_match_spans(collator, text, pat, "first"))
        chosen[i] = (not found) if neg else found
    out = []
    for i, keep in enumerate(chosen):
        if is_na(keep):
            out.append(NA)
        elif keep:
            out.append(texts[i] if i < len(texts) else _at(texts, i))
    return out
