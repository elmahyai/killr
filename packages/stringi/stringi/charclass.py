"""Character-class search and trim from stringi 1.8.9.

Patterns are ICU ``UnicodeSet`` patterns (``\\p{L}``, ``\\p{WhiteSpace}``,
``[a-z]``). Membership comes from ICU 76, Unicode 16. A match is one code
point. Positions are 1-based and inclusive.

Missing character values are :data:`stringi._na.NA`. The string ``"NA"`` is
text. ``from_`` is R's ``from``.

``stri_startswith_charclass`` at the position just past the last code point
tests U+0000, because the installed function reads the C string's trailing
NUL. ``stri_endswith_charclass`` does not.
"""

from __future__ import annotations

import warnings

import icu

from stringi._na import NA, is_na

_INT_MIN = -2147483647
_INT_MAX = 2147483647
_CACHE: dict[tuple[str, bool], bytes] = {}
_ICU_ERROR = {
    1: "U_ILLEGAL_ARGUMENT_ERROR",
    65538: "U_MALFORMED_SET",
    65540: "U_MALFORMED_UNICODE_ESCAPE",
}
_SIDES = ("both", "left", "right")
_SIDE_ERROR = "'arg' should be one of \u201cboth\u201d, \u201cleft\u201d, \u201cright\u201d"
_DEFAULT_TRIM = "\\P{Wspace}"


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
        number = value
    elif isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            warnings.warn("NAs introduced by coercion to integer range", stacklevel=4)
            return NA
        try:
            number = int(value)
        except OverflowError:
            warnings.warn("NAs introduced by coercion to integer range", stacklevel=4)
            return NA
    else:
        raise TypeError(f"{name} must be an integer")
    if number < _INT_MIN or number > _INT_MAX:
        warnings.warn("NAs introduced by coercion to integer range", stacklevel=4)
        return NA
    return number


def _as_ints(value: object, name: str) -> list:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        return [_one_int(item, name) for item in value]
    return [_one_int(value, name)]


def _one_logical(value: object, name: str, allow_na: bool) -> object:
    if is_na(value):
        if allow_na:
            return NA
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return value
    raise TypeError(f"{name} must be a single logical value")


def _as_logicals(value: object, name: str) -> list:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        return [_one_logical(item, name, True) for item in value]
    return [_one_logical(value, name, True)]


def _scalar(value: object, name: str, kind: str) -> object:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a single {kind} value")
        if len(value) > 1:
            warnings.warn(
                f"argument `{name}` should be a single {kind} value; "
                "only the first element is used",
                stacklevel=4,
            )
        value = value[0]
    return value


def _logical_1(value: object, name: str, allow_na: bool) -> object:
    return _one_logical(_scalar(value, name, "logical"), name, allow_na)


def _integer_1(value: object, name: str) -> int:
    number = _one_int(_scalar(value, name, "integer"), name)
    if is_na(number):
        raise ValueError(f"missing values in argument `{name}` is not supported")
    return number


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


def _at(values: list, index: int):
    return values[index % len(values)]


def _pattern_order(pattern_length: int, size: int) -> list[int]:
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


def _compile(pattern: str, negate: bool) -> bytes:
    key = (pattern, negate)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    try:
        charset = icu.UnicodeSet(pattern)
    except icu.ICUError as exc:
        code = exc.getErrorCode()
        message = exc.args[1] if len(exc.args) > 1 else str(exc)
        name = _ICU_ERROR.get(code)
        if name is None:
            raise ValueError(f"{message} (U_ERROR_{code})") from exc
        if not message.endswith("."):
            message += "."
        raise ValueError(f"{message} ({name})") from exc
    if negate:
        charset.complement("\u0000", "\U0010ffff")
    bits = bytearray(0x110000)
    for index in range(charset.getRangeCount()):
        start = ord(charset.getRangeStart(index))
        end = ord(charset.getRangeEnd(index))
        bits[start : end + 1] = b"\x01" * (end - start + 1)
    frozen = bytes(bits)
    _CACHE[key] = frozen
    return frozen


def _classes(patterns: list, negate: bool) -> list:
    out = []
    for pattern in patterns:
        if is_na(pattern):
            out.append(None)
        else:
            out.append(_compile(pattern, negate))
    return out


def _spans(text: str, bits: bytes, merge: bool) -> list[tuple[int, int]]:
    spans = []
    for index, char in enumerate(text):
        if bits[ord(char)]:
            if merge and spans and spans[-1][1] == index:
                spans[-1] = (spans[-1][0], index + 1)
            else:
                spans.append((index, index + 1))
    return spans


def _contains_any(text: str, bits: bytes) -> bool:
    for char in text:
        if bits[ord(char)]:
            return True
    return False


def _count_hits(text: str, bits: bytes) -> int:
    total = 0
    for char in text:
        total += bits[ord(char)]
    return total


def _no_match_row(get_length: bool) -> list:
    if get_length:
        return [-1, -1]
    return [NA, NA]


def _list2matrix(columns: list, fill, n_min: int) -> list:
    width = n_min
    for row in columns:
        if len(row) > width:
            width = len(row)
    matrix = []
    for row in columns:
        padded = list(row)
        if len(padded) < width:
            padded.extend([fill] * (width - len(padded)))
        matrix.append(padded)
    return matrix


def _replace_spans(text: str, spans: list[tuple[int, int]], replacement) -> object:
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


def _from_index(n: int, from_value: int):
    """Code-point index to test, or None for the trailing NUL."""
    if from_value == 1:
        index = 0
    elif from_value >= 0:
        where = from_value - 1
        index = 0 if where <= 0 else (where if where < n else n)
    else:
        where = -from_value
        index = n if where <= 0 else (n - where if where < n else 0)
    if index == n:
        return None
    return index


def _to_index(n: int, to_value: int):
    """Code-point index to test, or None when ``to`` lands at or before the start."""
    if to_value == -1:
        to_cur = n
    elif to_value >= 0:
        to_cur = 0 if to_value <= 0 else (to_value if to_value < n else n)
    else:
        where = -to_value - 1
        to_cur = n if where <= 0 else (n - where if where < n else 0)
    if to_cur <= 0:
        return None
    return to_cur - 1


def _match_side(side: object) -> str:
    if side is None:
        return "both"
    if isinstance(side, (list, tuple)) and not isinstance(side, str):
        if len(side) != 1:
            raise ValueError("'arg' must be of length 1")
        side = side[0]
    if is_na(side):
        raise ValueError(_SIDE_ERROR)
    if not isinstance(side, str):
        raise ValueError("'arg' must be NULL or a character vector")
    hits = [choice for choice in _SIDES if choice.startswith(side)]
    if len(hits) != 1:
        raise ValueError(_SIDE_ERROR)
    return hits[0]


def stri_count_charclass(str, pattern):
    """Count code points of ``pattern`` in each string.

    A missing string or pattern is ``NA``. An empty string with a real pattern
    counts as 0. An empty result is an empty list.
    """
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    size = _recycle_size([len(texts), len(patterns)])
    classes = _classes(patterns, False)
    out = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        if is_na(text) or bits is None:
            out.append(NA)
        else:
            out.append(_count_hits(text, bits))
    return out


def stri_detect_charclass(str, pattern, negate=False, max_count=-1):
    """Report whether each string contains a code point from ``pattern``.

    ``max_count`` stops after that many results of interest. Later elements,
    in stringi's pattern order, are ``NA``. ``max_count`` of 0 makes every
    element ``NA``. An empty string follows ``negate``.
    """
    neg = bool(_logical_1(negate, "negate", False))
    limit = _integer_1(max_count, "max_count")
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    size = _recycle_size([len(texts), len(patterns)])
    classes = _classes(patterns, False)
    out = [None] * size
    for index in _pattern_order(len(patterns), size):
        if limit == 0:
            out[index] = NA
            continue
        text = _at(texts, index)
        bits = _at(classes, index)
        if is_na(text) or bits is None:
            out[index] = NA
            continue
        found = _contains_any(text, bits)
        out[index] = (not found) if neg else found
        if limit > 0 and out[index] is True:
            limit -= 1
    return out


def stri_startswith_charclass(str, pattern, from_=1, negate=False):
    """Report whether the code point at ``from_`` is in ``pattern``.

    ``from_`` is 1-based. Negative values count back from the end, and ``-1``
    is the last code point. The index just past the end tests U+0000. An empty
    string therefore tests U+0000, not ``negate`` by itself.
    """
    neg = bool(_logical_1(negate, "negate", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    origins = _as_ints(from_, "from")
    size = _recycle_size([len(texts), len(patterns), len(origins)])
    classes = _classes(patterns, False)
    out = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        origin = _at(origins, index)
        if is_na(text) or bits is None or is_na(origin):
            out.append(NA)
            continue
        at = _from_index(len(text), origin)
        code = 0 if at is None else ord(text[at])
        found = bool(bits[code])
        out.append((not found) if neg else found)
    return out


def stri_endswith_charclass(str, pattern, to=-1, negate=False):
    """Report whether the code point at ``to`` is in ``pattern``.

    ``to`` of ``-1`` is the last code point. A ``to`` that lands at or before
    the start follows ``negate``. The trailing NUL is not tested.
    """
    neg = bool(_logical_1(negate, "negate", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    ends = _as_ints(to, "to")
    size = _recycle_size([len(texts), len(patterns), len(ends)])
    classes = _classes(patterns, False)
    out = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        end = _at(ends, index)
        if is_na(text) or bits is None or is_na(end):
            out.append(NA)
            continue
        at = _to_index(len(text), end)
        if at is None:
            out.append(neg)
            continue
        found = bool(bits[ord(text[at])])
        out.append((not found) if neg else found)
    return out


def _extract_edge(str, pattern, first: bool) -> list:
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    size = _recycle_size([len(texts), len(patterns)])
    classes = _classes(patterns, False)
    out = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        if is_na(text) or bits is None:
            out.append(NA)
            continue
        found = None
        for char in text:
            if bits[ord(char)]:
                found = char
                if first:
                    break
        out.append(NA if found is None else found)
    return out


def stri_extract_first_charclass(str, pattern):
    """Return the first matching code point, or ``NA``."""
    return _extract_edge(str, pattern, True)


def stri_extract_last_charclass(str, pattern):
    """Return the last matching code point, or ``NA``."""
    return _extract_edge(str, pattern, False)


def stri_extract_all_charclass(
    str, pattern, merge=True, simplify=False, omit_no_match=False
):
    """Return every match.

    ``merge`` joins consecutive matches into one string. A miss is a
    one-element ``NA`` vector unless ``omit_no_match`` is true. ``simplify``
    true pads a character matrix with empty strings. ``simplify`` missing pads
    with ``NA``.
    """
    merged = bool(_logical_1(merge, "merge", False))
    omit = bool(_logical_1(omit_no_match, "omit_no_match", False))
    simple = _logical_1(simplify, "simplify", True)
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    size = _recycle_size([len(texts), len(patterns)])
    classes = _classes(patterns, False)
    columns = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        if is_na(text) or bits is None:
            columns.append([NA])
            continue
        spans = _spans(text, bits, merged)
        if not spans:
            columns.append([] if omit else [NA])
        else:
            columns.append([text[start:end] for start, end in spans])
    if simple is False:
        return columns
    fill = NA if is_na(simple) else ""
    return _list2matrix(columns, fill, 0)


def _locate_edge(str, pattern, get_length, first: bool) -> list:
    length_mode = bool(_logical_1(get_length, "get_length", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    size = _recycle_size([len(texts), len(patterns)])
    classes = _classes(patterns, False)
    rows = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        if is_na(text) or bits is None:
            rows.append([NA, NA])
            continue
        row = _no_match_row(length_mode)
        for at, char in enumerate(text):
            if bits[ord(char)]:
                start = at + 1
                row = [start, 1 if length_mode else start]
                if first:
                    break
        rows.append(row)
    return rows


def stri_locate_first_charclass(str, pattern, get_length=False):
    """Locate the first matching code point.

    Each row is ``start``, ``end``. A miss is ``NA``, ``NA``. With
    ``get_length`` true the second column is the length, and a miss is
    ``-1``, ``-1``. A missing string stays ``NA``, ``NA``.
    """
    return _locate_edge(str, pattern, get_length, True)


def stri_locate_last_charclass(str, pattern, get_length=False):
    """Locate the last matching code point."""
    return _locate_edge(str, pattern, get_length, False)


def stri_locate_all_charclass(
    str, pattern, merge=True, omit_no_match=False, get_length=False
):
    """Locate every match.

    The result is a list of matrices. Columns are ``start`` and ``end``, or
    ``start`` and ``length`` when ``get_length`` is true. ``merge`` joins a
    run of matches into one row. A miss is one ``NA`` row, or ``-1``, ``-1``
    when ``get_length`` is true. ``omit_no_match`` returns no rows.
    """
    merged = bool(_logical_1(merge, "merge", False))
    omit = bool(_logical_1(omit_no_match, "omit_no_match", False))
    length_mode = bool(_logical_1(get_length, "get_length", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    size = _recycle_size([len(texts), len(patterns)])
    classes = _classes(patterns, False)
    matrices = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        if is_na(text) or bits is None:
            matrices.append([[NA, NA]])
            continue
        spans = _spans(text, bits, merged)
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


def _replace_vectorized(texts, patterns, replacements, merge: bool, mode: str) -> list:
    size = _recycle_size([len(texts), len(patterns), len(replacements)])
    classes = _classes(patterns, False)
    out = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        repl = _at(replacements, index)
        if is_na(text) or bits is None:
            out.append(NA)
            continue
        spans = _spans(text, bits, merge if mode == "all" else False)
        if mode == "first":
            spans = spans[:1]
        elif mode == "last":
            spans = spans[-1:]
        out.append(_replace_spans(text, spans, repl))
    return out


def stri_replace_first_charclass(str, pattern, replacement):
    """Replace the first matching code point. A miss returns the original string."""
    return _replace_vectorized(
        _as_strings(str, "str"),
        _as_strings(pattern, "pattern"),
        _as_strings(replacement, "replacement"),
        False,
        "first",
    )


def stri_replace_last_charclass(str, pattern, replacement):
    """Replace the last matching code point. A miss returns the original string."""
    return _replace_vectorized(
        _as_strings(str, "str"),
        _as_strings(pattern, "pattern"),
        _as_strings(replacement, "replacement"),
        False,
        "last",
    )


def stri_replace_all_charclass(
    str,
    pattern,
    replacement,
    merge=False,
    vectorize_all=True,
    vectorise_all=None,
):
    """Replace matching code points.

    With ``vectorize_all`` true, ``str``, ``pattern``, and ``replacement`` are
    recycled together. With it false, each pattern is applied to every string,
    in order, and ``pattern`` must be at least as long as ``replacement``.
    ``merge`` replaces a whole run with one copy of the replacement.
    ``vectorise_all``, when given, overrides ``vectorize_all``. A miss keeps
    the original string, even when the replacement is missing.
    """
    if vectorise_all is not None:
        vectorize_all = vectorise_all
    together = bool(_logical_1(vectorize_all, "vectorize_all", False))
    merged = bool(_logical_1(merge, "merge", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    replacements = _as_strings(replacement, "replacement")
    if together:
        return _replace_vectorized(texts, patterns, replacements, merged, "all")
    if len(texts) == 0:
        return []
    if len(patterns) < len(replacements) or len(patterns) == 0 or len(replacements) == 0:
        raise ValueError("vector length not consistent with other arguments")
    if len(patterns) % len(replacements) != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            stacklevel=2,
        )
    if len(patterns) == 1:
        return _replace_vectorized(texts, patterns, replacements, merged, "all")
    classes = _classes(patterns, False)
    if any(bits is None for bits in classes):
        return [NA] * len(texts)
    current = list(texts)
    for index, bits in enumerate(classes):
        repl = replacements[index % len(replacements)]
        for slot, text in enumerate(current):
            if is_na(text):
                continue
            spans = _spans(text, bits, merged)
            if not spans:
                continue
            current[slot] = _replace_spans(text, spans, repl)
    return current


def _split_one(text, bits, n_value, omit_value, tokens_only: bool) -> list:
    if is_na(text) or bits is None or is_na(n_value):
        return [NA]
    if n_value >= _INT_MAX - 1:
        raise ValueError("incorrect argument `n`; value too large")
    if n_value == 0:
        return []
    if n_value < 0:
        n_cur = _INT_MAX
    else:
        n_cur = n_value + (1 if tokens_only else 0)
    length = len(text)
    fields = [(0, 0)]
    cursor = 0
    taken = 1
    drop = omit_value is True
    while cursor < length and taken < n_cur:
        cursor += 1
        if bits[ord(text[cursor - 1])]:
            if drop and fields[-1][0] == fields[-1][1]:
                fields[-1] = (cursor, cursor)
            else:
                fields.append((cursor, cursor))
                taken += 1
        else:
            start, _end = fields[-1]
            fields[-1] = (start, cursor)
    if taken == n_cur:
        start, _end = fields[-1]
        fields[-1] = (start, length)
    if drop and fields[-1][0] == fields[-1][1]:
        fields.pop()
    if tokens_only and 0 <= n_value < _INT_MAX:
        while len(fields) > n_value:
            fields.pop()
    missing_empty = is_na(omit_value)
    pieces = []
    for start, end in fields:
        if start == end and missing_empty:
            pieces.append(NA)
        else:
            pieces.append(text[start:end])
    return pieces


def stri_split_charclass(
    str,
    pattern,
    n=-1,
    omit_empty=False,
    tokens_only=False,
    simplify=False,
):
    """Split each string on code points from ``pattern``.

    ``n`` below 0 returns every piece. A positive ``n`` returns ``n - 1``
    pieces and the remainder, unless ``tokens_only`` is true, which keeps at
    most ``n`` whole pieces. ``omit_empty`` true drops empty pieces. The
    missing value replaces them with ``NA``. ``simplify`` true pads a
    character matrix with empty strings; the missing value pads with ``NA``.
    The width is at least the largest positive ``n``.
    """
    tokens = bool(_logical_1(tokens_only, "tokens_only", False))
    simple = _logical_1(simplify, "simplify", True)
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    counts = _as_ints(n, "n")
    empties = _as_logicals(omit_empty, "omit_empty")
    size = _recycle_size([len(texts), len(patterns), len(counts), len(empties)])
    classes = _classes(patterns, False)
    columns = []
    for index in range(size):
        columns.append(
            _split_one(
                _at(texts, index),
                _at(classes, index),
                _at(counts, index),
                _at(empties, index),
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


def stri_subset_charclass(str, pattern, omit_na=False, negate=False):
    """Keep the strings that contain a code point from ``pattern``.

    ``pattern`` cannot be longer than ``str`` when ``str`` is not empty.
    A missing string or pattern is kept as ``NA`` unless ``omit_na`` is true.
    ``negate`` keeps the strings that do not match. An empty string follows
    ``negate``.
    """
    neg = bool(_logical_1(negate, "negate", False))
    drop_na = bool(_logical_1(omit_na, "omit_na", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    if len(texts) > 0 and len(texts) < len(patterns):
        raise ValueError("vector length not consistent with other arguments")
    size = _recycle_size([len(texts), len(patterns)])
    if size == 0:
        return []
    classes = _classes(patterns, False)
    out = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        if is_na(text) or bits is None:
            if not drop_na:
                out.append(NA)
            continue
        found = _contains_any(text, bits)
        if neg:
            found = not found
        if found:
            out.append(text)
    return out


def _trim_one(text: str, bits: bytes, left: bool, right: bool) -> str:
    length = len(text)
    start = 0
    end = length
    if left:
        while start < length and not bits[ord(text[start])]:
            start += 1
    if right and start < length:
        end = length
        while end > 0 and not bits[ord(text[end - 1])]:
            end -= 1
    return text[start:end]


def _trim_vector(str, pattern, negate, left: bool, right: bool) -> list:
    neg = bool(_logical_1(negate, "negate", False))
    texts = _as_strings(str, "str")
    patterns = _as_strings(pattern, "pattern")
    size = _recycle_size([len(texts), len(patterns)])
    classes = _classes(patterns, neg)
    out = []
    for index in range(size):
        text = _at(texts, index)
        bits = _at(classes, index)
        if is_na(text) or bits is None:
            out.append(NA)
        else:
            out.append(_trim_one(text, bits, left, right))
    return out


def stri_trim_both(str, pattern=_DEFAULT_TRIM, negate=False):
    """Keep from the first preserved code point through the last.

    ``pattern`` is the class to preserve. ``negate`` true trims that class
    instead. The default preserves every non-whitespace code point.
    """
    return _trim_vector(str, pattern, negate, True, True)


def stri_trim_left(str, pattern=_DEFAULT_TRIM, negate=False):
    """Drop a leading run of code points that are not preserved."""
    return _trim_vector(str, pattern, negate, True, False)


def stri_trim_right(str, pattern=_DEFAULT_TRIM, negate=False):
    """Drop a trailing run of code points that are not preserved."""
    return _trim_vector(str, pattern, negate, False, True)


def stri_trim(str, side="both", pattern=_DEFAULT_TRIM, negate=False):
    """Trim one or both sides.

    ``side`` is ``both``, ``left``, or ``right``. A unique prefix is enough.
    ``NULL`` (``None``) selects ``both``.
    """
    chosen = _match_side(side)
    if chosen == "left":
        return stri_trim_left(str, pattern, negate)
    if chosen == "right":
        return stri_trim_right(str, pattern, negate)
    return stri_trim_both(str, pattern, negate)
