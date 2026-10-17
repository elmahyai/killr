"""ICU regular-expression search from stringi 1.8.9.

Patterns are compiled with :class:`icu.RegexMatcher`. Match indexes that ICU
reports in UTF-16 code units are converted to 1-based inclusive code points.
A zero-length match has an end one less than its start. Missing character
values are :data:`stringi._na.NA`. The string ``"NA"`` is text.

``opts_regex`` is a dict of the settings that were supplied. Passing further
keyword arguments merges them through :func:`stringi.opts.stri_opts_regex`,
which is how R's ``...`` reaches ``stri_opts_regex``. Replacement text uses
ICU backreferences (``$1``, ``${name}``, ``\\1``). :func:`stri_replace_rstr`
rewrites a ``gsub`` replacement into that form.
"""

from __future__ import annotations

import warnings

import icu

from stringi._na import NA, is_na
from stringi.opts import stri_opts_regex

_INT_MAX = 2147483647
_CACHE: dict[tuple, icu.RegexMatcher] = {}

_FLAGS = {
    "case_insensitive": int(icu.URegexpFlag.CASE_INSENSITIVE),
    "comments": int(icu.URegexpFlag.COMMENTS),
    "dotall": int(icu.URegexpFlag.DOTALL),
    "literal": int(icu.URegexpFlag.LITERAL),
    "multiline": int(icu.URegexpFlag.MULTILINE),
    "unix_lines": int(icu.URegexpFlag.UNIX_LINES),
    "uword": int(icu.URegexpFlag.UWORD),
    "error_on_unknown_escapes": int(icu.URegexpFlag.ERROR_ON_UNKNOWN_ESCAPES),
}

# stringi's ICUError::getICUerrorName for the regex codes PyICU raises.
_ICU_ERRORS = {
    1: ("Illegal argument.", "U_ILLEGAL_ARGUMENT_ERROR"),
    8: ("Trying to access the index that is out of bounds.", "U_INDEX_OUTOFBOUNDS_ERROR"),
    66304: ("An internal error (bug) was detected in ICU.", "U_REGEX_INTERNAL_ERROR"),
    66305: ("Syntax error in regex pattern.", "U_REGEX_RULE_SYNTAX"),
    66306: ("RegexMatcher in invalid state for requested operation.", "U_REGEX_INVALID_STATE"),
    66307: ("Unrecognized backslash escape sequence in pattern.", "U_REGEX_BAD_ESCAPE_SEQUENCE"),
    66308: ("Incorrect Unicode property.", "U_REGEX_PROPERTY_SYNTAX"),
    66309: ("Use of regex feature that is not yet implemented.", "U_REGEX_UNIMPLEMENTED"),
    66310: ("Incorrectly nested parentheses in regex pattern.", "U_REGEX_MISMATCHED_PAREN"),
    66311: ("Decimal number is too large.", "U_REGEX_NUMBER_TOO_BIG"),
    66312: ("Error in {min,max} interval.", "U_REGEX_BAD_INTERVAL"),
    66313: ("In {min,max}, max is less than min.", "U_REGEX_MAX_LT_MIN"),
    66314: ("Back-reference to a non-existent capture group.", "U_REGEX_INVALID_BACK_REF"),
    66315: ("Invalid value for match mode flags.", "U_REGEX_INVALID_FLAG"),
    66316: (
        "Look-Behind pattern matches must have a bounded maximum length.",
        "U_REGEX_LOOK_BEHIND_LIMIT",
    ),
    66317: (
        "Regexes cannot have UnicodeSets containing strings.",
        "U_REGEX_SET_CONTAINS_STRING",
    ),
    66319: (
        "Missing closing bracket on a bracket expression.",
        "U_REGEX_MISSING_CLOSE_BRACKET",
    ),
    66320: ("In a character range [x-y], x is greater than y.", "U_REGEX_INVALID_RANGE"),
    66321: ("Regular expression backtrack stack overflow.", "U_REGEX_STACK_OVERFLOW"),
    66322: ("Maximum allowed match time exceeded.", "U_REGEX_TIME_OUT"),
    66323: ("Matching operation aborted by user callback fn.", "U_REGEX_STOPPED_BY_CALLER"),
    66324: ("Pattern exceeds limits on size or complexity.", "U_REGEX_PATTERN_TOO_BIG"),
    66325: ("Invalid capture group name.", "U_REGEX_INVALID_CAPTURE_GROUP_NAME"),
}


class _Matrix(list):
    """Character matrix stored by row.

    A list of rows compares equal to a plain list. ``colnames`` is set when
    the single pattern has a named capture group. ``ncol`` keeps the width of
    a matrix that has no rows.
    """

    def __init__(self, rows, colnames=None, ncol=None):
        super().__init__(rows)
        self.colnames = colnames
        self.ncol = len(rows[0]) if rows else (0 if ncol is None else ncol)


class _CaptureList(list):
    """Capture-group matrices, named when the pattern names a group."""

    def __init__(self, items, names=None):
        super().__init__(items)
        self.names = names


def _raise_icu(exc: BaseException, context: str | None = None) -> None:
    code = exc.getErrorCode() if isinstance(exc, icu.ICUError) else None
    if code in _ICU_ERRORS:
        message, name = _ICU_ERRORS[code]
    else:
        message, name = "Unknown ICU error or warning.", f"U_ERROR_{code}"
    if context is not None:
        raise ValueError(f"{message} ({name}, context=`{context}`)") from None
    raise ValueError(f"{message} ({name})") from None


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


def _one_string(value: object, name: str):
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty character vector")
        if len(value) > 1:
            warnings.warn(
                f"argument `{name}` should be one character string; taking the first element",
                stacklevel=3,
            )
        value = value[0]
    if is_na(value):
        return NA
    if isinstance(value, str):
        return value
    raise TypeError(f"{name} must be a string")


def _one_int(value: object, name: str) -> object:
    if is_na(value):
        return NA
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        if value < -_INT_MAX - 1 or value > _INT_MAX:
            warnings.warn(f"NAs introduced by coercion to integer ({name})", stacklevel=4)
            return NA
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")) or abs(value) > _INT_MAX:
            warnings.warn(f"NAs introduced by coercion to integer ({name})", stacklevel=4)
            return NA
        return int(value)
    raise TypeError(f"{name} must be an integer")


def _as_ints(value: object, name: str) -> list:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        return [_one_int(item, name) for item in value]
    return [_one_int(value, name)]


def _logical_token(value: object, name: str, allow_na: bool):
    if is_na(value):
        if allow_na:
            return NA
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            warnings.warn("NAs introduced by coercion", stacklevel=4)
            if allow_na:
                return NA
            raise ValueError(f"missing values in argument `{name}` is not supported")
        return value != 0
    if isinstance(value, str):
        token = value.strip().lower()
        if token in ("true", "t"):
            return True
        if token in ("false", "f"):
            return False
        warnings.warn("NAs introduced by coercion", stacklevel=4)
        if allow_na:
            return NA
        raise ValueError(f"missing values in argument `{name}` is not supported")
    raise TypeError(f"{name} must be a logical value")


def _one_logical(value: object, name: str, allow_na: bool):
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            warnings.warn(
                f"argument `{name}` should be a single logical value; only the first element is used",
                stacklevel=4,
            )
        value = value[0]
    return _logical_token(value, name, allow_na)


def _as_logicals(value: object, name: str) -> list:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        return [_logical_token(item, name, True) for item in value]
    return [_logical_token(value, name, True)]


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
    """Order used by stringi's pattern container. It matters for max_count."""
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


def _resolve_opts(opts_regex, kwargs: dict) -> dict:
    if kwargs:
        if opts_regex is None:
            base: dict = {}
        elif isinstance(opts_regex, dict):
            base = dict(opts_regex)
        else:
            raise TypeError("argument `opts_regex` should be a list")
        for key in kwargs:
            if key in base:
                raise TypeError(
                    f'formal argument "{key}" matched by multiple actual arguments'
                )
        return stri_opts_regex(**{**base, **kwargs})
    if opts_regex is None:
        return {}
    if not isinstance(opts_regex, dict):
        raise TypeError("argument `opts_regex` should be a list")
    return dict(opts_regex)


def _read_opts(opts: dict) -> tuple[int, int, int]:
    flags = 0
    stack_limit = 0
    time_limit = 0
    for key, raw in opts.items():
        if key in _FLAGS:
            if _logical_token(raw, key, False):
                flags |= _FLAGS[key]
        elif key == "stack_limit":
            stack_limit = _option_int(raw, key)
        elif key == "time_limit":
            time_limit = _option_int(raw, key)
        else:
            warnings.warn(
                f"incorrect opts_regex setting: '{key}'; ignoring",
                stacklevel=4,
            )
    return flags, stack_limit, time_limit


def _option_int(value: object, name: str) -> int:
    number = _one_int(value, name)
    if is_na(number):
        raise ValueError(f"missing values in argument `{name}` is not supported")
    return int(number)


def _matcher(pattern: str, flags: int, time_limit: int, stack_limit: int) -> icu.RegexMatcher:
    time_key = time_limit if time_limit > 0 else 0
    stack_key = stack_limit if stack_limit > 0 else 0
    key = (pattern, flags, time_key, stack_key)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    try:
        matcher = icu.RegexMatcher(icu.UnicodeString(pattern), flags)
    except icu.ICUError as exc:
        _raise_icu(exc, pattern)
    if time_key:
        try:
            matcher.setTimeLimit(time_key)
        except icu.ICUError as exc:
            _raise_icu(exc, pattern)
    if stack_key:
        try:
            matcher.setStackLimit(stack_key)
        except icu.ICUError as exc:
            _raise_icu(exc, pattern)
    _CACHE[key] = matcher
    return matcher


def _nonbmp(text: str) -> bool:
    return any(ord(ch) > 0xFFFF for ch in text)


def _utf16_map(text: str) -> list[int] | None:
    """Map a UTF-16 index to the code-point index at that unit.

    The last entry is the code-point length, so an exclusive end converts
    without adding one. ``None`` means the string is in the BMP and the
    indexes already agree.
    """
    if not _nonbmp(text):
        return None
    mapping = []
    code_point = 0
    for ch in text:
        mapping.append(code_point)
        if ord(ch) > 0xFFFF:
            mapping.append(code_point)
        code_point += 1
    mapping.append(code_point)
    return mapping


def _cp(mapping: list[int] | None, utf16_index: int) -> int:
    if mapping is None:
        return utf16_index
    return mapping[utf16_index]


def _advance(text: str, mapping: list[int] | None, end: int) -> int:
    """UTF-16 index one code point after a zero-length match."""
    if mapping is None:
        return end + 1
    pos = 0
    for ch in text:
        width = 2 if ord(ch) > 0xFFFF else 1
        if pos == end:
            return pos + width
        pos += width
    return end + 1


def _row(mapping, start_u: int, end_u: int, get_length: bool):
    if start_u < 0 or end_u < 0:
        return [-1, -1] if get_length else [NA, NA]
    start_cp = _cp(mapping, start_u)
    end_cp = _cp(mapping, end_u)
    start_1 = start_cp + 1
    if get_length:
        return [start_1, end_cp - start_1 + 1]
    return [start_1, end_cp]


def _no_match_row(get_length: bool):
    return [-1, -1] if get_length else [NA, NA]


def _capture_names(pattern: str) -> list[str]:
    """Names of capturing groups, in order. An unnamed group is ``""``.

    The scan follows stringi's pattern walk: a backslash skips the next
    character, a bracket expression is skipped, and ``(?<name>`` is a named
    group. Look-behind ``(?<=`` and ``(?<!`` are not names.
    """
    names: list[str] = []
    chars = pattern
    i = 0
    n = len(chars)
    while i < n:
        c = chars[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            i += 1
            while i < n and chars[i] != "]":
                if chars[i] == "\\":
                    i += 2
                else:
                    i += 1
            i += 1
            continue
        if c == "(":
            if i + 1 < n and chars[i + 1] == "?":
                if i + 2 < n and chars[i + 2] == "<" and not (
                    i + 3 < n and chars[i + 3] in "=!"
                ):
                    j = i + 3
                    name = []
                    while j < n and (
                        ("A" <= chars[j] <= "Z")
                        or ("a" <= chars[j] <= "z")
                        or ("0" <= chars[j] <= "9")
                    ):
                        name.append(chars[j])
                        j += 1
                    names.append("".join(name) if j < n and chars[j] == ">" else "")
                i += 1
                continue
            names.append("")
            i += 1
            continue
        i += 1
    return names


def _drop_matcher(matcher) -> None:
    for key, cached in list(_CACHE.items()):
        if cached is matcher:
            del _CACHE[key]
            return


def _iter_found(matcher, text: str, text_us, limited: bool, mapping):
    """Yield after each match. The matcher is left on that match.

    ``find()`` without an index does not surface a time or stack limit.
    ``find(start)`` does, so a positive limit uses that form and advances
    one code point after a zero-length match.
    """
    matcher.reset(text_us)
    if not limited:
        while True:
            try:
                found = matcher.find()
            except icu.ICUError as exc:
                _drop_matcher(matcher)
                _raise_icu(exc)
            if not found:
                return
            yield
        return
    pos = 0
    limit = text_us.length()
    while pos <= limit:
        try:
            found = matcher.find(pos)
        except icu.ICUError as exc:
            _drop_matcher(matcher)
            _raise_icu(exc)
        if not found:
            return
        start = matcher.start(0)
        end = matcher.end(0)
        yield
        if start == end:
            pos = _advance(text, mapping, end)
        else:
            pos = end
        if pos > limit:
            return


def _group_piece(matcher, index: int, missing):
    try:
        start = matcher.start(index)
    except icu.ICUError as exc:
        _raise_icu(exc)
    if start < 0:
        return missing
    try:
        return matcher.group(index)
    except icu.ICUError as exc:
        _raise_icu(exc)


def _hits(pattern: str, text: str, flags: int, time_limit: int, stack_limit: int, groups: bool):
    matcher = _matcher(pattern, flags, time_limit, stack_limit)
    text_us = icu.UnicodeString(text)
    mapping = _utf16_map(text)
    limited = time_limit > 0 or stack_limit > 0
    found = []
    try:
        n_groups = matcher.groupCount() if groups else 0
    except icu.ICUError as exc:
        _raise_icu(exc, pattern)
    for _ in _iter_found(matcher, text, text_us, limited, mapping):
        try:
            start = matcher.start(0)
            end = matcher.end(0)
        except icu.ICUError as exc:
            _raise_icu(exc)
        if groups:
            parts = [_group_piece(matcher, 0, NA)]
            spans = [(start, end)]
            for index in range(1, n_groups + 1):
                try:
                    g_start = matcher.start(index)
                    g_end = matcher.end(index)
                except icu.ICUError as exc:
                    _raise_icu(exc)
                spans.append((g_start, g_end))
                parts.append(_group_piece(matcher, index, None))
            found.append((start, end, parts, spans))
        else:
            found.append((start, end, None, None))
    return found, n_groups, mapping


def _count_hits(pattern, text, flags, time_limit, stack_limit) -> int:
    matcher = _matcher(pattern, flags, time_limit, stack_limit)
    text_us = icu.UnicodeString(text)
    mapping = _utf16_map(text) if (time_limit > 0 or stack_limit > 0) else None
    count = 0
    for _ in _iter_found(matcher, text, text_us, time_limit > 0 or stack_limit > 0, mapping):
        count += 1
    return count


def _finds(pattern, text, flags, time_limit, stack_limit) -> bool:
    matcher = _matcher(pattern, flags, time_limit, stack_limit)
    text_us = icu.UnicodeString(text)
    limited = time_limit > 0 or stack_limit > 0
    mapping = _utf16_map(text) if limited else None
    matcher.reset(text_us)
    try:
        if limited:
            return bool(matcher.find(0))
        return bool(matcher.find())
    except icu.ICUError as exc:
        _drop_matcher(matcher)
        _raise_icu(exc)


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


def _match_arg(value: object, choices: tuple[str, ...]) -> str:
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("'arg' must be of length 1")
        if len(value) > 1:
            warnings.warn("first element used of 'mode' argument", stacklevel=3)
        value = value[0]
    if not isinstance(value, str) or not value:
        shown = ", ".join(f'"{choice}"' for choice in choices)
        raise ValueError(f"'{value}' should be one of {shown}")
    hits = [choice for choice in choices if choice.startswith(value)]
    if len(hits) != 1:
        shown = ", ".join(f'"{choice}"' for choice in choices)
        raise ValueError(f"'{value}' should be one of {shown}")
    return hits[0]


def _colnames(pattern: str, n_groups: int):
    names = _capture_names(pattern)
    if len(names) != n_groups:
        names = [""] * n_groups
    if not any(names):
        return None
    return [""] + names


def _prepare(str, pattern, kwargs, opts_regex):
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    opts = _read_opts(_resolve_opts(opts_regex, kwargs))
    return texts, patterns, opts


def stri_count_regex(str, pattern, opts_regex=None, **kwargs):
    """Count regex matches in each string.

    An empty pattern or a missing string or pattern is ``NA`` and an empty
    pattern warns. An empty string is searched, so ``.*`` counts as 1.
    """
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if is_na(text) or is_na(pat) or pat == "":
            out.append(NA)
            continue
        out.append(_count_hits(pat, text, flags, time_limit, stack_limit))
    return out


def stri_detect_regex(
    str,
    pattern,
    negate=False,
    max_count=-1,
    opts_regex=None,
    **kwargs,
):
    """Report whether each string contains a regex match.

    ``max_count`` stops after that many results of interest. Later elements,
    in stringi's pattern order, are ``NA``. ``negate`` flips a real match.
    An empty string is searched.
    """
    neg = bool(_one_logical(negate, "negate", False))
    limit = _one_int(max_count, "max_count")
    if is_na(limit):
        raise ValueError("missing values in argument `max_count` is not supported")
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    out = [None] * size
    for i in _pattern_order(len(patterns), size):
        if limit == 0:
            out[i] = NA
            continue
        text = _at(texts, i)
        pat = _at(patterns, i)
        if is_na(text) or is_na(pat) or pat == "":
            out[i] = NA
            continue
        found = _finds(pat, text, flags, time_limit, stack_limit)
        out[i] = (not found) if neg else found
        if limit > 0 and out[i] is True:
            limit -= 1
    return out


def _extract_edge(str, pattern, opts_regex, kwargs, first: bool):
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if is_na(text) or is_na(pat) or pat == "":
            out.append(NA)
            continue
        hits, _n_groups, _mapping = _hits(pat, text, flags, time_limit, stack_limit, True)
        if not hits:
            out.append(NA)
        else:
            chosen = hits[0] if first else hits[-1]
            out.append(chosen[2][0])
    return out


def stri_extract_first_regex(str, pattern, opts_regex=None, **kwargs):
    """Return the first regex match in each string, or ``NA``."""
    return _extract_edge(str, pattern, opts_regex, kwargs, True)


def stri_extract_last_regex(str, pattern, opts_regex=None, **kwargs):
    """Return the last non-overlapping regex match, or ``NA``.

    The search runs from the start and skips overlaps, so the last match is
    the last one ``find`` reports.
    """
    return _extract_edge(str, pattern, opts_regex, kwargs, False)


def stri_extract_all_regex(
    str,
    pattern,
    simplify=False,
    omit_no_match=False,
    opts_regex=None,
    **kwargs,
):
    """Return every non-overlapping regex match.

    The default is a list of character vectors. A miss is a one-element ``NA``
    vector unless ``omit_no_match`` is true. ``simplify=True`` pads a character
    matrix with empty strings. ``simplify`` missing (the ``NA`` object) pads
    with ``NA``.
    """
    omit = bool(_one_logical(omit_no_match, "omit_no_match", False))
    simple = _one_logical(simplify, "simplify", True)
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    columns = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if is_na(text) or is_na(pat) or pat == "":
            columns.append([NA])
            continue
        hits, _n_groups, _mapping = _hits(pat, text, flags, time_limit, stack_limit, True)
        if not hits:
            columns.append([] if omit else [NA])
        else:
            columns.append([hit[2][0] for hit in hits])
    if simple is False:
        return columns
    fill = NA if is_na(simple) else ""
    return _list2matrix(columns, fill, 0)


def _locate_rows(hits, mapping, get_length: bool, which: int | None = None):
    rows = []
    for hit in hits:
        if which is None:
            start_u, end_u = hit[0], hit[1]
        else:
            start_u, end_u = hit[3][which]
        rows.append(_row(mapping, start_u, end_u, get_length))
    return rows


def stri_locate_all_regex(
    str,
    pattern,
    omit_no_match=False,
    capture_groups=False,
    get_length=False,
    opts_regex=None,
    **kwargs,
):
    """Locate every non-overlapping regex match.

    Each element is a matrix of ``start``, ``end`` rows, or ``start``,
    ``length`` when ``get_length`` is true. A miss is one ``NA`` row, or
    ``-1``, ``-1`` for an empty match result when ``get_length`` is true.
    A missing string stays ``NA``, ``NA``. ``omit_no_match`` drops the miss
    row. ``capture_groups=True`` attaches a ``capture_groups`` list of the
    same kind of matrix for each parenthesized group.
    """
    omit = bool(_one_logical(omit_no_match, "omit_no_match", False))
    groups = bool(_one_logical(capture_groups, "capture_groups", False))
    length_mode = bool(_one_logical(get_length, "get_length", False))
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    matrices = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if is_na(pat) or pat == "":
            if pat == "":
                warnings.warn("empty search patterns are not supported", stacklevel=2)
            if groups:
                holder = _CaptureList([[NA, NA]])
                holder.capture_groups = _CaptureList([])
                matrices.append(holder)
            else:
                matrices.append([[NA, NA]])
            continue
        if is_na(text):
            holder = [[NA, NA]]
            if groups:
                n_groups = _matcher(pat, flags, time_limit, stack_limit).groupCount()
                names = _capture_names(pat)
                if len(names) != n_groups or not any(names):
                    names = None
                blocks = []
                for _group in range(n_groups):
                    blocks.append([[NA, NA]])
                wrapped = _CaptureList(holder)
                wrapped.capture_groups = _CaptureList(blocks, names)
                matrices.append(wrapped)
            else:
                matrices.append(holder)
            continue
        hits, n_groups, mapping = _hits(pat, text, flags, time_limit, stack_limit, groups)
        if not hits:
            rows = [] if omit else [_no_match_row(length_mode)]
        else:
            rows = _locate_rows(hits, mapping, length_mode)
        if groups:
            names = _capture_names(pat)
            if len(names) != n_groups or not any(names):
                names = None
            blocks = []
            for group_index in range(n_groups):
                if not hits:
                    blocks.append([] if omit else [_no_match_row(length_mode)])
                else:
                    blocks.append(_locate_rows(hits, mapping, length_mode, group_index + 1))
            wrapped = _CaptureList(rows)
            wrapped.capture_groups = _CaptureList(blocks, names)
            matrices.append(wrapped)
        else:
            matrices.append(rows)
    return matrices


def _locate_edge(str, pattern, capture_groups, get_length, opts_regex, kwargs, first: bool):
    groups = bool(_one_logical(capture_groups, "capture_groups", False))
    length_mode = bool(_one_logical(get_length, "get_length", False))
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    rows = []
    group_rows: list[list] = []
    max_groups = 0
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if is_na(pat) or pat == "":
            if pat == "":
                warnings.warn("empty search patterns are not supported", stacklevel=2)
            rows.append([NA, NA])
            continue
        if groups:
            n_groups = _matcher(pat, flags, time_limit, stack_limit).groupCount()
            while len(group_rows) < n_groups:
                group_rows.append([[NA, NA] for _ in range(size)])
            if n_groups > max_groups:
                max_groups = n_groups
        if is_na(text):
            rows.append([NA, NA])
            continue
        if length_mode:
            rows.append([-1, -1])
        else:
            rows.append([NA, NA])
        hits, n_groups, mapping = _hits(pat, text, flags, time_limit, stack_limit, groups)
        if not hits:
            if groups and length_mode:
                for group_index in range(n_groups):
                    group_rows[group_index][i] = [-1, -1]
            continue
        chosen = hits[0] if first else hits[-1]
        rows[i] = _row(mapping, chosen[0], chosen[1], length_mode)
        if groups:
            for group_index in range(n_groups):
                start_u, end_u = chosen[3][group_index + 1]
                group_rows[group_index][i] = _row(mapping, start_u, end_u, length_mode)
    if not groups:
        return rows
    names = None
    if len(patterns) == 1 and patterns and not is_na(patterns[0]) and patterns[0] != "":
        parsed = _capture_names(patterns[0])
        if len(parsed) == max_groups and any(parsed):
            names = parsed
    wrapped = _CaptureList(rows)
    wrapped.capture_groups = _CaptureList(group_rows, names)
    return wrapped


def stri_locate_first_regex(
    str,
    pattern,
    capture_groups=False,
    get_length=False,
    opts_regex=None,
    **kwargs,
):
    """Locate the first regex match.

    The result is a matrix of ``start``, ``end`` rows. A miss is ``NA``,
    ``NA``, or ``-1``, ``-1`` when ``get_length`` is true. A missing string
    stays ``NA``. ``capture_groups=True`` attaches one matrix per group.
    Group names are kept when ``pattern`` is a single pattern.
    """
    return _locate_edge(str, pattern, capture_groups, get_length, opts_regex, kwargs, True)


def stri_locate_last_regex(
    str,
    pattern,
    capture_groups=False,
    get_length=False,
    opts_regex=None,
    **kwargs,
):
    """Locate the last non-overlapping regex match.

    The search runs from the start and skips overlaps.
    """
    return _locate_edge(str, pattern, capture_groups, get_length, opts_regex, kwargs, False)


def _replace_text(text: str, pattern: str, replacement: str, mode: str, flags, time_limit, stack_limit):
    matcher = _matcher(pattern, flags, time_limit, stack_limit)
    text_us = icu.UnicodeString(text)
    if is_na(replacement):
        if _finds(pattern, text, flags, time_limit, stack_limit):
            return NA
        return text
    repl_us = icu.UnicodeString(replacement)
    try:
        if mode == "all":
            matcher.reset(text_us)
            return str(matcher.replaceAll(repl_us))
        if mode == "first":
            matcher.reset(text_us)
            return str(matcher.replaceFirst(repl_us))
    except icu.ICUError as exc:
        _drop_matcher(matcher)
        _raise_icu(exc)
    limited = time_limit > 0 or stack_limit > 0
    mapping = _utf16_map(text) if limited else None
    start = end = -1
    for _ in _iter_found(matcher, text, text_us, limited, mapping):
        start = matcher.start(0)
        end = matcher.end(0)
    if start < 0:
        return text
    try:
        matcher.find(start)
        out = icu.UnicodeString()
        matcher.appendReplacement(out, repl_us)
        out.append(text_us, end, text_us.length() - end)
        return str(out)
    except icu.ICUError as exc:
        _drop_matcher(matcher)
        _raise_icu(exc)


def _replace_vectorized(str, pattern, replacement, opts_regex, kwargs, mode: str):
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    replacements = _as_strings(replacement, "replacement")
    flags, stack_limit, time_limit = _read_opts(_resolve_opts(opts_regex, kwargs))
    size = _recycle_size([len(texts), len(patterns), len(replacements)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        repl = _at(replacements, i)
        if is_na(text) or is_na(pat) or pat == "":
            out.append(NA)
            continue
        out.append(_replace_text(text, pat, repl, mode, flags, time_limit, stack_limit))
    return out


def stri_replace_first_regex(str, pattern, replacement, opts_regex=None, **kwargs):
    """Replace the first regex match. A miss returns the original string.

    A missing replacement removes the string when the pattern matches and
    leaves it unchanged otherwise. Backreferences use ICU's replacement syntax.
    """
    return _replace_vectorized(str, pattern, replacement, opts_regex, kwargs, "first")


def stri_replace_last_regex(str, pattern, replacement, opts_regex=None, **kwargs):
    """Replace the last non-overlapping regex match.

    The search runs from the start and skips overlaps.
    """
    return _replace_vectorized(str, pattern, replacement, opts_regex, kwargs, "last")


def stri_replace_all_regex(
    str,
    pattern,
    replacement,
    vectorize_all=True,
    vectorise_all=None,
    opts_regex=None,
    **kwargs,
):
    """Replace regex matches.

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
        return _replace_vectorized(str, pattern, replacement, opts_regex, kwargs, "all")
    texts = _as_strings(str, "str")
    if len(texts) == 0:
        return []
    patterns = _as_strings(pattern, "pattern")
    replacements = _as_strings(replacement, "replacement")
    flags, stack_limit, time_limit = _read_opts(_resolve_opts(opts_regex, kwargs))
    if len(patterns) < len(replacements) or len(patterns) == 0 or len(replacements) == 0:
        raise ValueError("vector length not consistent with other arguments")
    if len(patterns) % len(replacements) != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            stacklevel=2,
        )
    _warn_empty(patterns)
    if len(patterns) == 1:
        return _replace_vectorized(texts, patterns, replacements, opts_regex, kwargs, "all")
    current = list(texts)
    for index, pat in enumerate(patterns):
        repl = replacements[index % len(replacements)]
        if is_na(pat):
            return [NA] * len(current)
        if pat == "":
            warnings.warn("empty search patterns are not supported", stacklevel=2)
            return [NA] * len(current)
        for j, text in enumerate(current):
            if is_na(text):
                continue
            current[j] = _replace_text(text, pat, repl, "all", flags, time_limit, stack_limit)
    return current


def _split_one(text, pattern, n_value, omit_value, tokens_only: bool, flags, time_limit, stack_limit):
    if is_na(n_value):
        return [NA]
    if is_na(text) or is_na(pattern) or pattern == "":
        return [NA]
    if text == "":
        if is_na(omit_value):
            return [NA]
        if omit_value or n_value == 0:
            return []
        return [""]
    if n_value >= _INT_MAX - 1:
        raise ValueError("incorrect argument `n`; value too large")
    if n_value == 0:
        return []
    unlimited = n_value < 0
    limit = None if unlimited else n_value + (1 if tokens_only else 0)
    hits, _n_groups, mapping = _hits(pattern, text, flags, time_limit, stack_limit, False)
    fields = [[0, 0]]
    taken = 1
    n_cp = len(text)
    for start_u, end_u, _parts, _spans in hits:
        if limit is not None and taken >= limit:
            break
        start = _cp(mapping, start_u)
        stop = _cp(mapping, end_u)
        if omit_value is True and fields[-1][0] == start:
            fields[-1][0] = stop
        else:
            fields[-1][1] = start
            fields.append([stop, stop])
            taken += 1
    fields[-1][1] = n_cp
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


def stri_split_regex(
    str,
    pattern,
    n=-1,
    omit_empty=False,
    tokens_only=False,
    simplify=False,
    opts_regex=None,
    **kwargs,
):
    """Split each string on regex matches.

    ``n`` below 0 returns every piece. A positive ``n`` returns ``n - 1``
    pieces and the remainder, unless ``tokens_only`` is true, which keeps at
    most ``n`` whole pieces. ``omit_empty=True`` drops empty pieces.
    ``omit_empty`` equal to the missing value replaces them with ``NA``.
    ``simplify=True`` returns a character matrix padded with empty strings.
    The missing value pads with ``NA``. The width is at least the largest
    positive ``n``.
    """
    tokens = bool(_one_logical(tokens_only, "tokens_only", False))
    simple = _one_logical(simplify, "simplify", True)
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    counts = _as_ints(n, "n")
    empties = _as_logicals(omit_empty, "omit_empty")
    size = _recycle_size([len(texts), len(patterns), len(counts), len(empties)])
    _warn_empty(patterns)
    columns = []
    for i in range(size):
        columns.append(
            _split_one(
                _at(texts, i),
                _at(patterns, i),
                _at(counts, i),
                _at(empties, i),
                tokens,
                flags,
                time_limit,
                stack_limit,
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


def stri_subset_regex(
    str,
    pattern,
    omit_na=False,
    negate=False,
    opts_regex=None,
    **kwargs,
):
    """Keep the strings that contain a regex match.

    ``pattern`` cannot be longer than ``str`` when ``str`` is not empty.
    A missing string or an empty pattern is kept as ``NA`` unless ``omit_na``
    is true. ``negate`` keeps the strings that do not match. An empty string
    is searched.
    """
    neg = bool(_one_logical(negate, "negate", False))
    drop_na = bool(_one_logical(omit_na, "omit_na", False))
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    if len(texts) > 0 and len(texts) < len(patterns):
        raise ValueError("vector length not consistent with other arguments")
    size = _recycle_size([len(texts), len(patterns)])
    if size == 0:
        _warn_empty(patterns)
        return []
    _warn_empty(patterns)
    chosen = [False] * size
    for i in _pattern_order(len(patterns), size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if is_na(text) or is_na(pat) or pat == "":
            chosen[i] = False if drop_na else NA
            continue
        found = _finds(pat, text, flags, time_limit, stack_limit)
        chosen[i] = (not found) if neg else found
    out = []
    for i, keep in enumerate(chosen):
        if is_na(keep):
            out.append(NA)
        elif keep:
            out.append(_at(texts, i))
    return out


def _match_first_last(str, pattern, cg_missing, opts_regex, kwargs, first: bool):
    missing = _one_string(cg_missing, "cg_missing")
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    width = 1
    rows_src: list[list | None] = [None] * size
    if size == 0 and patterns:
        colnames = None
        for pat in patterns:
            if is_na(pat) or pat == "":
                if pat == "":
                    warnings.warn("empty search patterns are not supported", stacklevel=2)
                continue
            n_groups = _matcher(pat, flags, time_limit, stack_limit).groupCount()
            width = max(width, n_groups + 1)
            if len(patterns) == 1:
                colnames = _colnames(pat, n_groups)
        return _Matrix([], colnames=colnames, ncol=width)
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if is_na(pat) or pat == "":
            if pat == "":
                warnings.warn("empty search patterns are not supported", stacklevel=2)
            continue
        n_groups = _matcher(pat, flags, time_limit, stack_limit).groupCount()
        width = max(width, n_groups + 1)
        if is_na(text):
            continue
        hits, _n_groups, _mapping = _hits(pat, text, flags, time_limit, stack_limit, True)
        cells = [missing] * (n_groups + 1)
        if hits:
            chosen = hits[0] if first else hits[-1]
            for index, piece in enumerate(chosen[2]):
                cells[index] = missing if piece is None else piece
        rows_src[i] = cells
    colnames = None
    if len(patterns) == 1 and patterns and not is_na(patterns[0]) and patterns[0] != "":
        colnames = _colnames(patterns[0], _matcher(patterns[0], flags, time_limit, stack_limit).groupCount())
    rows = []
    for cells in rows_src:
        if cells is None:
            rows.append([NA] * width)
        else:
            padded = list(cells)
            if len(padded) < width:
                padded.extend([NA] * (width - len(padded)))
            rows.append(padded)
    return _Matrix(rows, colnames=colnames, ncol=width)


def stri_match_first_regex(str, pattern, cg_missing=NA, opts_regex=None, **kwargs):
    """Return the first match and its capture groups as a character matrix.

    Each row is one string. Column 0 is the whole match. A group that did not
    participate is ``cg_missing``. A miss fills that pattern's columns with
    ``cg_missing``. A missing string stays ``NA``. Named groups label the
    columns when ``pattern`` is a single pattern. The first column name is empty.
    """
    return _match_first_last(str, pattern, cg_missing, opts_regex, kwargs, True)


def stri_match_last_regex(str, pattern, cg_missing=NA, opts_regex=None, **kwargs):
    """Return the last non-overlapping match and its capture groups.

    The search runs from the start and skips overlaps.
    """
    return _match_first_last(str, pattern, cg_missing, opts_regex, kwargs, False)


def stri_match_all_regex(
    str,
    pattern,
    omit_no_match=False,
    cg_missing=NA,
    opts_regex=None,
    **kwargs,
):
    """Return every match and its capture groups.

    Each element is a character matrix. A miss is one row of ``cg_missing``
    unless ``omit_no_match`` is true, in which case the matrix has no rows.
    A missing string is one row of ``NA``. An empty pattern is a one-by-one
    ``NA`` matrix.
    """
    omit = bool(_one_logical(omit_no_match, "omit_no_match", False))
    missing = _one_string(cg_missing, "cg_missing")
    texts, patterns, (flags, stack_limit, time_limit) = _prepare(str, pattern, kwargs, opts_regex)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if is_na(pat) or pat == "":
            if pat == "":
                warnings.warn("empty search patterns are not supported", stacklevel=2)
            out.append(_Matrix([[NA]], ncol=1))
            continue
        n_groups = _matcher(pat, flags, time_limit, stack_limit).groupCount()
        colnames = _colnames(pat, n_groups)
        width = n_groups + 1
        if is_na(text):
            out.append(_Matrix([[NA] * width], colnames=colnames, ncol=width))
            continue
        hits, _n_groups, _mapping = _hits(pat, text, flags, time_limit, stack_limit, True)
        if not hits:
            rows = [] if omit else [[missing] * width]
        else:
            rows = []
            for hit in hits:
                cells = []
                for piece in hit[2]:
                    cells.append(missing if piece is None else piece)
                rows.append(cells)
        out.append(_Matrix(rows, colnames=colnames, ncol=width))
    return out


def stri_match(str, regex, mode="first", **kwargs):
    """Extract regex matches and capture groups.

    ``mode`` is ``"first"`` (the default), ``"all"``, or ``"last"``. A unique
    prefix is accepted. This calls the corresponding ``stri_match_*_regex``
    function. ``regex`` is the pattern.
    """
    chosen = _match_arg(mode, ("first", "all", "last"))
    if chosen == "first":
        return stri_match_first_regex(str, regex, **kwargs)
    if chosen == "last":
        return stri_match_last_regex(str, regex, **kwargs)
    return stri_match_all_regex(str, regex, **kwargs)


stri_match_all = stri_match_all_regex
stri_match_first = stri_match_first_regex
stri_match_last = stri_match_last_regex


def _rstr_one(text: str) -> str:
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "$":
            out.append("\\$")
        elif ch == "\\":
            i += 1
            if i >= n:
                break
            nxt = text[i]
            if nxt == "$":
                out.append("\\$")
            elif nxt == "\\":
                out.append("\\\\")
            elif "1" <= nxt <= "9":
                out.append("$")
                out.append(nxt)
                if i + 1 < n and "0" <= text[i + 1] <= "9":
                    out.append("\\")
            else:
                out.append(nxt)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def stri_replace_rstr(x):
    """Rewrite a ``gsub`` replacement into ICU replacement syntax.

    ``$`` becomes ``\\$`` and ``\\1`` becomes ``$1``. A trailing backslash is
    dropped. ``\\12`` becomes ``$1\\2`` so the second digit is not part of the
    group number. A letter escape such as ``\\a`` keeps the letter.
    """
    values = _as_strings(x, "x")
    return [NA if is_na(value) else _rstr_one(value) for value in values]
