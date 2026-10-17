"""Literal search from stringi 1.8.9.

Patterns are matched as text, not as regular expressions. Case-insensitive
search maps each code point with ICU ``u_toupper``: a character whose Python
``upper`` is a single code point uses that mapping, and a character whose
``upper`` is longer stays unchanged. Overlap advances one code point and is
honored by count, locate-all, and extract-all. The installed replace functions
ignore it.

Missing character values are :data:`stringi._na.NA`. The string ``"NA"`` is
text. Positions from the locate functions are 1-based inclusive code-point
indexes. ``from_`` is R's ``from``; ``from`` is not a Python parameter name.
"""

from __future__ import annotations

import warnings

from stringi._na import NA, is_na

_INT_MAX = 2147483647
_UPPER: dict[str, str] = {}


def _upper_char(ch: str) -> str:
    cached = _UPPER.get(ch)
    if cached is None:
        mapped = ch.upper()
        cached = mapped if len(mapped) == 1 else ch
        _UPPER[ch] = cached
    return cached


def _fold(text: str) -> str:
    """Single-code-point uppercase, the same length as ``text``."""
    if text.isascii():
        return text.upper()
    return "".join(_upper_char(ch) for ch in text)


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


def _read_opts(opts_fixed, case_insensitive, overlap, allow_overlap: bool) -> tuple[bool, bool]:
    if opts_fixed is None:
        opts: dict = {}
    elif isinstance(opts_fixed, dict):
        opts = dict(opts_fixed)
    else:
        raise TypeError("opts_fixed should be a list")
    if case_insensitive is not None:
        if "case_insensitive" in opts:
            raise TypeError(
                'formal argument "case_insensitive" matched by multiple actual arguments'
            )
        opts["case_insensitive"] = case_insensitive
    if overlap is not None:
        if "overlap" in opts:
            raise TypeError('formal argument "overlap" matched by multiple actual arguments')
        opts["overlap"] = overlap
    folded = False
    overlapping = False
    for key, val in opts.items():
        if key == "case_insensitive":
            folded = bool(_one_logical(val, "case_insensitive", False))
        elif key == "overlap" and allow_overlap:
            overlapping = bool(_one_logical(val, "overlap", False))
        else:
            warnings.warn(
                f"incorrect opts_fixed setting: '{key}'; ignoring",
                stacklevel=4,
            )
    return folded, overlapping


def _at(values: list, index: int):
    return values[index % len(values)]


def _view(text: str, pattern: str, case_insensitive: bool) -> tuple[str, str]:
    if case_insensitive:
        return _fold(text), _fold(pattern)
    return text, pattern


def _iter_matches(haystack: str, needle: str, overlap: bool):
    start = 0
    step = 1 if overlap else len(needle)
    limit = len(haystack)
    while start <= limit:
        found = haystack.find(needle, start)
        if found < 0:
            return
        yield found
        start = found + step


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


def _starts(text: str, pattern: str, index: int, case_insensitive: bool) -> bool:
    end = index + len(pattern)
    if end > len(text):
        return False
    piece = text[index:end]
    if case_insensitive:
        return _fold(piece) == _fold(pattern)
    return piece == pattern


def _ends(text: str, pattern: str, end: int, case_insensitive: bool) -> bool:
    start = end - len(pattern)
    if start < 0 or end > len(text):
        return False
    piece = text[start:end]
    if case_insensitive:
        return _fold(piece) == _fold(pattern)
    return piece == pattern


def _locate_rows(text: str, pattern: str, case_insensitive: bool, overlap: bool, get_length: bool, mode: str):
    haystack, needle = _view(text, pattern, case_insensitive)
    if mode == "all":
        starts = list(_iter_matches(haystack, needle, overlap))
    elif mode == "first":
        found = haystack.find(needle)
        starts = [] if found < 0 else [found]
    else:
        found = haystack.rfind(needle)
        starts = [] if found < 0 else [found]
    plen = len(pattern)
    rows = []
    for start in starts:
        start_1 = start + 1
        if get_length:
            rows.append([start_1, plen])
        else:
            rows.append([start_1, start + plen])
    return rows


def _no_match_row(get_length: bool):
    if get_length:
        return [-1, -1]
    return [NA, NA]


def _replace_spans(text: str, pattern: str, replacement: str, case_insensitive: bool, mode: str):
    haystack, needle = _view(text, pattern, case_insensitive)
    if mode == "last":
        found = haystack.rfind(needle)
        starts = [] if found < 0 else [found]
    elif mode == "first":
        found = haystack.find(needle)
        starts = [] if found < 0 else [found]
    else:
        starts = list(_iter_matches(haystack, needle, False))
    if not starts:
        return text
    if is_na(replacement):
        return NA
    plen = len(pattern)
    parts = []
    cursor = 0
    for start in starts:
        parts.append(text[cursor:start])
        parts.append(replacement)
        cursor = start + plen
    parts.append(text[cursor:])
    return "".join(parts)


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


def _split_one(text, pattern, n_value, omit_value, tokens_only: bool, case_insensitive: bool):
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
    haystack, needle = _view(text, pattern, case_insensitive)
    fields = [[0, 0]]
    taken = 1
    for start in _iter_matches(haystack, needle, False):
        if limit is not None and taken >= limit:
            break
        stop = start + len(pattern)
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


def stri_count_fixed(
    str,
    pattern,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Count literal matches of ``pattern`` in each string.

    An empty pattern or a missing string or pattern is ``NA``. An empty string
    with a non-empty pattern counts as 0. ``overlap`` counts matches that
    share code points.
    """
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    folded, overlapping = _read_opts(opts_fixed, case_insensitive, overlap, True)
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
            haystack, needle = _view(text, pat, folded)
            out.append(sum(1 for _ in _iter_matches(haystack, needle, overlapping)))
    return out


def stri_detect_fixed(
    str,
    pattern,
    negate=False,
    max_count=-1,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Report whether each string contains a literal pattern.

    ``max_count`` stops after that many results of interest. Later elements are
    ``NA``. The elements are not always visited from left to right when
    ``pattern`` is longer than one. An empty string follows ``negate``.
    ``overlap`` is ignored.
    """
    neg = bool(_one_logical(negate, "negate", False))
    limit = _one_int(max_count, "max_count")
    if is_na(limit):
        raise ValueError("missing value in argument max_count is not allowed")
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    folded, _overlapping = _read_opts(opts_fixed, case_insensitive, overlap, False)
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
            haystack, needle = _view(text, pat, folded)
            found = haystack.find(needle) >= 0
            out[i] = (not found) if neg else found
        if limit > 0 and out[i] is True:
            limit -= 1
    return out


def stri_startswith_fixed(
    str,
    pattern,
    from_=1,
    negate=False,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Report whether a literal pattern matches at ``from_``.

    ``from_`` is R's ``from``: a 1-based code-point index. Negative values
    count back from the end, and ``-1`` is the last code point. An empty
    pattern or a missing value is ``NA``. An empty string follows ``negate``.
    """
    neg = bool(_one_logical(negate, "negate", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    origins = _as_ints(from_, "from")
    folded, _overlapping = _read_opts(opts_fixed, case_insensitive, overlap, False)
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
            matched = _starts(text, pat, _start_index(len(text), origin), folded)
            out.append((not matched) if neg else matched)
    return out


def stri_endswith_fixed(
    str,
    pattern,
    to=-1,
    negate=False,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Report whether a literal pattern ends at ``to``.

    ``to`` is a 1-based code-point index. ``-1`` is the end of the string.
    An empty pattern or a missing value is ``NA``. An empty string follows
    ``negate``.
    """
    neg = bool(_one_logical(negate, "negate", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    ends = _as_ints(to, "to")
    folded, _overlapping = _read_opts(opts_fixed, case_insensitive, overlap, False)
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
            matched = _ends(text, pat, _end_index(len(text), end), folded)
            out.append((not matched) if neg else matched)
    return out


def stri_extract_first_fixed(
    str,
    pattern,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Return the first literal match in each string, or ``NA``."""
    return _extract_edge(str, pattern, opts_fixed, case_insensitive, overlap, "first")


def stri_extract_last_fixed(
    str,
    pattern,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Return the last literal match in each string, or ``NA``.

    The last match is the rightmost one. Overlap is ignored.
    """
    return _extract_edge(str, pattern, opts_fixed, case_insensitive, overlap, "last")


def _extract_edge(str, pattern, opts_fixed, case_insensitive, overlap, mode: str):
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    folded, _overlapping = _read_opts(opts_fixed, case_insensitive, overlap, False)
    size = _recycle_size([len(texts), len(patterns)])
    _warn_empty(patterns)
    out = []
    for i in range(size):
        text = _at(texts, i)
        pat = _at(patterns, i)
        if _missing_pattern(text, pat) or text == "":
            out.append(NA)
            continue
        rows = _locate_rows(text, pat, folded, False, False, mode)
        if not rows:
            out.append(NA)
        else:
            start, end = rows[0]
            out.append(text[start - 1 : end])
    return out


def stri_extract_all_fixed(
    str,
    pattern,
    simplify=False,
    omit_no_match=False,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Return every literal match.

    The default is a list of character vectors. A missing match is a one-element
    ``NA`` vector unless ``omit_no_match`` is true, in which case that vector is
    empty. ``simplify=True`` pads a character matrix with empty strings.
    ``simplify`` missing (the ``NA`` object) pads with ``NA``. ``overlap`` is
    honored.
    """
    omit = bool(_one_logical(omit_no_match, "omit_no_match", False))
    simple = _one_logical(simplify, "simplify", True)
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    folded, overlapping = _read_opts(opts_fixed, case_insensitive, overlap, True)
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
        rows = _locate_rows(text, pat, folded, overlapping, False, "all")
        if not rows:
            columns.append([] if omit else [NA])
        else:
            columns.append([text[start - 1 : end] for start, end in rows])
    if simple is False:
        return columns
    fill = NA if is_na(simple) else ""
    return _list2matrix(columns, fill, 0)


def stri_locate_first_fixed(
    str,
    pattern,
    get_length=False,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Locate the first literal match.

    Each row is ``start``, ``end``. Both are 1-based and inclusive. A miss is
    ``NA``, ``NA``. With ``get_length=True`` the second column is the length,
    and a miss or an empty string is ``-1``, ``-1``. A missing string stays
    ``NA``.
    """
    return _locate_edge(str, pattern, get_length, opts_fixed, case_insensitive, overlap, "first")


def stri_locate_last_fixed(
    str,
    pattern,
    get_length=False,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Locate the rightmost literal match. Overlap is ignored."""
    return _locate_edge(str, pattern, get_length, opts_fixed, case_insensitive, overlap, "last")


def _locate_edge(str, pattern, get_length, opts_fixed, case_insensitive, overlap, mode: str):
    length_mode = bool(_one_logical(get_length, "get_length", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    folded, _overlapping = _read_opts(opts_fixed, case_insensitive, overlap, False)
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
        found = _locate_rows(text, pat, folded, False, length_mode, mode)
        rows.append(found[0] if found else _no_match_row(length_mode))
    return rows


def stri_locate_all_fixed(
    str,
    pattern,
    omit_no_match=False,
    get_length=False,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Locate every literal match.

    The result is a list of matrices. Each matrix has columns ``start`` and
    ``end``, or ``start`` and ``length`` when ``get_length`` is true. A miss is
    one ``NA`` row unless ``omit_no_match`` is true, in which case the matrix
    has no rows. An empty string uses ``-1`` when ``get_length`` is true.
    ``overlap`` is honored.
    """
    omit = bool(_one_logical(omit_no_match, "omit_no_match", False))
    length_mode = bool(_one_logical(get_length, "get_length", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    folded, overlapping = _read_opts(opts_fixed, case_insensitive, overlap, True)
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
        rows = _locate_rows(text, pat, folded, overlapping, length_mode, "all")
        if not rows:
            matrices.append([] if omit else [_no_match_row(length_mode)])
        else:
            matrices.append(rows)
    return matrices


def stri_replace_first_fixed(
    str,
    pattern,
    replacement,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Replace the first literal match. A miss returns the original string."""
    return _replace_vectorized(
        str, pattern, replacement, opts_fixed, case_insensitive, overlap, "first"
    )


def stri_replace_last_fixed(
    str,
    pattern,
    replacement,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Replace the rightmost literal match. Overlap is ignored."""
    return _replace_vectorized(
        str, pattern, replacement, opts_fixed, case_insensitive, overlap, "last"
    )


def stri_replace_all_fixed(
    str,
    pattern,
    replacement,
    vectorize_all=True,
    vectorise_all=None,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Replace literal matches.

    With ``vectorize_all=True`` (the default), ``str``, ``pattern``, and
    ``replacement`` are recycled together. With ``vectorize_all=False``, each
    pattern is applied to every string, in order. ``pattern`` must be at least
    as long as ``replacement``. The installed function ignores ``overlap``.
    ``vectorise_all``, when given, overrides ``vectorize_all``.
    """
    if vectorise_all is not None:
        vectorize_all = vectorise_all
    together = bool(_one_logical(vectorize_all, "vectorize_all", False))
    if together:
        return _replace_vectorized(
            str, pattern, replacement, opts_fixed, case_insensitive, overlap, "all"
        )
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
    if len(patterns) == 1:
        return _replace_vectorized(
            texts, patterns, replacements, opts_fixed, case_insensitive, overlap, "all"
        )
    folded, _overlapping = _read_opts(opts_fixed, case_insensitive, overlap, False)
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
            if is_na(text):
                continue
            current[j] = _replace_spans(text, pat, repl, folded, "all")
    return current


def _replace_vectorized(str, pattern, replacement, opts_fixed, case_insensitive, overlap, mode: str):
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    replacements = _as_strings(replacement, "replacement")
    folded, _overlapping = _read_opts(opts_fixed, case_insensitive, overlap, False)
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
            out.append(_replace_spans(text, pat, repl, folded, mode))
    return out


def stri_split_fixed(
    str,
    pattern,
    n=-1,
    omit_empty=False,
    tokens_only=False,
    simplify=False,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Split each string on a literal delimiter.

    ``n`` below 0 returns every piece. A positive ``n`` returns ``n-1`` pieces
    and the remainder, unless ``tokens_only`` is true, which keeps at most
    ``n`` whole pieces. ``omit_empty=True`` drops empty pieces.
    ``omit_empty`` equal to the missing value replaces them with ``NA``.
    ``simplify=True`` returns a character matrix padded with empty strings;
    the missing value pads with ``NA``. The width is at least the largest
    positive ``n``. ``overlap`` is ignored.
    """
    tokens = bool(_one_logical(tokens_only, "tokens_only", False))
    simple = _one_logical(simplify, "simplify", True)
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    counts = _as_ints(n, "n")
    empties = _as_logicals(omit_empty, "omit_empty")
    folded, _overlapping = _read_opts(opts_fixed, case_insensitive, overlap, False)
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
                folded,
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


def stri_subset_fixed(
    str,
    pattern,
    omit_na=False,
    negate=False,
    opts_fixed=None,
    case_insensitive=None,
    overlap=None,
):
    """Keep the strings that contain a literal pattern.

    ``pattern`` cannot be longer than ``str`` when ``str`` is not empty.
    A missing string or an empty pattern is kept as ``NA`` unless ``omit_na``
    is true. ``negate`` keeps the strings that do not match. An empty string
    follows ``negate``. ``overlap`` is ignored.
    """
    neg = bool(_one_logical(negate, "negate", False))
    drop_na = bool(_one_logical(omit_na, "omit_na", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    if len(texts) > 0 and len(texts) < len(patterns):
        raise ValueError("vector length not consistent with other arguments")
    folded, _overlapping = _read_opts(opts_fixed, case_insensitive, overlap, False)
    size = _recycle_size([len(texts), len(patterns)])
    if size == 0:
        return []
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
        haystack, needle = _view(text, pat, folded)
        found = haystack.find(needle) >= 0
        chosen[i] = (not found) if neg else found
    out = []
    for i, keep in enumerate(chosen):
        if is_na(keep):
            out.append(NA)
        elif keep:
            out.append(texts[i] if i < len(texts) else _at(texts, i))
    return out
