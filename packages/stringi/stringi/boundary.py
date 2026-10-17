"""Text-boundary search from stringi 1.8.9.

Breaks come from ICU 76 ``BreakIterator`` (character, word, sentence, and
line). Indexes from that iterator are UTF-16 code units. These functions
report 1-based inclusive code points, which is what stringi returns after
it converts UTF-8 byte offsets.

A ``skip_*`` flag drops every segment whose ending boundary has that rule
status. The skipped text is not merged into the next segment. An omitted
flag is false. ``opts_brkiter`` keeps only the settings that were supplied.

Missing character values are :data:`stringi._na.NA`. The string ``"NA"``
is text. ``stri_split_lines1`` omits the empty field after a final newline.
``omit_empty`` equal to ``NA`` is truthy and drops empty lines.
"""

from __future__ import annotations

import ctypes
import warnings

import icu

from stringi._na import NA, is_na
from stringi.opts import stri_opts_brkiter

_TEXT = str
_INT_MAX = 2147483647
_DONE = icu.BreakIterator.DONE
_TYPES = ("character", "line_break", "sentence", "word")
_SKIP_RANGES = {
    "skip_word_none": (0, 100),
    "skip_word_number": (100, 200),
    "skip_word_letter": (200, 300),
    "skip_word_kana": (300, 400),
    "skip_word_ideo": (400, 500),
    "skip_line_soft": (0, 100),
    "skip_line_hard": (100, 200),
    "skip_sentence_term": (0, 100),
    "skip_sentence_sep": (100, 200),
}
_NEWLINES = frozenset("\n\r\v\f\x85\u2028\u2029")
_FACTORIES = {
    "character": icu.BreakIterator.createCharacterInstance,
    "line_break": icu.BreakIterator.createLineInstance,
    "sentence": icu.BreakIterator.createSentenceInstance,
    "word": icu.BreakIterator.createWordInstance,
}
_VALID_LOCALE = icu.ULocDataLocaleType.VALID_LOCALE
_ROOT_WARNING = (
    "A resource bundle lookup returned a result either from the root or the default locale."
)
_ITERATORS: dict[tuple, object] = {}

_icuuc = ctypes.CDLL("libicuuc.so.76")
_uloc_canonicalize = _icuuc.uloc_canonicalize_76
_uloc_canonicalize.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32),
]
_uloc_canonicalize.restype = ctypes.c_int32
_u_error_name = _icuuc.u_errorName_76
_u_error_name.argtypes = [ctypes.c_int32]
_u_error_name.restype = ctypes.c_char_p


def _error_name(code: int) -> str:
    raw = _u_error_name(code)
    if raw is None:
        return "U_ZERO_ERROR"
    return raw.decode("ascii", "replace")


def _raise_icu(exc: icu.ICUError) -> None:
    code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else 0
    message = "ICU error."
    if len(exc.args) > 1 and isinstance(exc.args[1], tuple) and exc.args[1]:
        if isinstance(exc.args[1][0], str):
            message = exc.args[1][0]
    elif exc.args and isinstance(exc.args[0], str):
        message = exc.args[0]
    raise ValueError(f"{message} ({_error_name(code)})") from None


def _canonicalize(text: str) -> str:
    source = text.encode("utf-8")
    buf = ctypes.create_string_buffer(512)
    err = ctypes.c_int32(0)
    size = _uloc_canonicalize(source, buf, 512, ctypes.byref(err))
    if err.value > 0:
        raise ValueError(f"Illegal argument. ({_error_name(err.value)})")
    if size < 0:
        raise ValueError(f"Illegal argument. ({_error_name(err.value)})")
    return buf.raw[:size].decode("utf-8", "replace")


def _is_c_locale(text: str) -> bool:
    return bool(text) and text[0] in "Cc" and (len(text) == 1 or text[1] == ".")


def _default_locale_name() -> str:
    name = icu.Locale.getDefault().getName()
    if _is_c_locale(name):
        return "en_US_POSIX"
    return name


def _as_strings(value: object) -> list:
    if value is None:
        return []
    if is_na(value) or isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            if is_na(item) or isinstance(item, str):
                out.append(item)
            else:
                raise TypeError("str must be a string or a list of strings")
        return out
    raise TypeError("str must be a string or a list of strings")


def _one_string_setting(value: object, name: str, na_message: str) -> object:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            warnings.warn(
                f"argument `{name}` should be a single character string; only the first element is used",
                stacklevel=4,
            )
        value = value[0]
    if is_na(value):
        raise ValueError(na_message)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a single string")
    return value


def _one_logical(value: object, name: str, allow_na: bool) -> object:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            warnings.warn(
                f"argument `{name}` should be a single logical value; only the first element is used",
                stacklevel=4,
            )
        value = value[0]
    if is_na(value):
        if allow_na:
            return NA
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return value
    raise TypeError(f"{name} must be a single logical value")


def _as_logicals(value: object, name: str) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        return [_one_logical(item, name, True) for item in value]
    return [_one_logical(value, name, True)]


def _one_int(value: object, name: str) -> object:
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        raise TypeError(f"{name} must be an integer")
    if is_na(value):
        return NA
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            warnings.warn("NAs introduced by coercion", stacklevel=4)
            return NA
        return int(value)
    raise TypeError(f"{name} must be an integer")


def _as_ints(value: object, name: str) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple)) and not isinstance(value, str):
        return [_one_int(item, name) for item in value]
    return [_one_int(value, name)]


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


def _match_type(option: str) -> int:
    excluded = [False] * len(_TYPES)
    for k, ch in enumerate(option):
        for i, name in enumerate(_TYPES):
            if excluded[i]:
                continue
            if k >= len(name) or name[k] != ch:
                excluded[i] = True
            elif k + 1 == len(name) and k + 1 == len(option):
                return i
    which = -1
    for i, gone in enumerate(excluded):
        if gone:
            continue
        if which < 0:
            which = i
        else:
            return -1
    return which


def _resolve_locale(value: object) -> tuple[str | None, bool]:
    """Return the ICU locale name and whether it was set explicitly.

    ``None`` means the process default. An explicit locale that falls back
    to root warns. ``root`` and ``und`` canonicalize to empty and therefore
    use the default, so they do not warn.
    """
    if value is None or value == "":
        return None, False
    text = _one_string_setting(
        value,
        "locale",
        "missing values in argument `locale` is not supported",
    )
    if text is None or text == "":
        return None, False
    name = _canonicalize(text).strip(" \t\r\n")
    if name == "":
        return None, False
    if _is_c_locale(name):
        return "en_US_POSIX", True
    if name[0] == "@":
        return _default_locale_name() + name, True
    return name, True


def _merge_opts(opts_brkiter, kwargs: dict) -> dict:
    if not kwargs:
        if opts_brkiter is None:
            return {}
        if isinstance(opts_brkiter, dict):
            return dict(opts_brkiter)
        raise TypeError("incorrect break iterator option specifier, see ?stri_opts_brkiter")
    if opts_brkiter is None:
        base: dict = {}
    elif isinstance(opts_brkiter, dict):
        base = dict(opts_brkiter)
    else:
        raise TypeError("incorrect break iterator option specifier, see ?stri_opts_brkiter")
    for key in kwargs:
        if key in base:
            raise TypeError(f'formal argument "{key}" matched by multiple actual arguments')
    return stri_opts_brkiter(**base, **kwargs)


class _Engine:
    """One break iterator and the skip ranges for a single call."""

    def __init__(self, opts: dict):
        self.skips: list[tuple[int, int]] = []
        self.kind = "line_break"
        self.rules = ""
        self.locale: str | None = None
        self.explicit = False
        self._iterator = None
        self._warned = False
        if "type" in opts:
            type_value = _one_string_setting(opts["type"], "type", "incorrect option for `type`")
            if type_value is None:
                type_value = ""
            matched = _match_type(type_value)
            if matched >= 0:
                self.kind = _TYPES[matched]
            elif type_value != "":
                self.rules = type_value
            else:
                self.kind = "character"
        if "locale" in opts:
            self.locale, self.explicit = _resolve_locale(opts["locale"])
        for name, bounds in _SKIP_RANGES.items():
            if name not in opts:
                continue
            flag = _one_logical(opts[name], name, False)
            if flag:
                self.skips.append(bounds)

    def iterator(self):
        if self._iterator is None:
            key = ("rules", self.rules) if self.rules else (self.kind, self.locale)
            cached = _ITERATORS.get(key)
            if cached is None:
                try:
                    if self.rules:
                        cached = icu.RuleBasedBreakIterator(self.rules)
                    else:
                        loc = icu.Locale.getDefault() if self.locale is None else icu.Locale(self.locale)
                        cached = _FACTORIES[self.kind](loc)
                except icu.ICUError as exc:
                    _raise_icu(exc)
                _ITERATORS[key] = cached
            self._iterator = cached
        if self.explicit and not self.rules and not self._warned:
            self._warned = True
            valid = self._iterator.getLocaleID(_VALID_LOCALE)
            if valid == "root":
                warnings.warn(_ROOT_WARNING, stacklevel=5)
        return self._iterator

    def _code_points(self, text: str, u16: int) -> int:
        mapping = getattr(self, "_map", None)
        if mapping is None:
            return u16
        return mapping[u16]

    def _prepare_map(self, text: str) -> None:
        if text.isascii():
            self._map = None
            return
        supplementary = False
        units = 0
        for ch in text:
            if ord(ch) > 0xFFFF:
                supplementary = True
                units += 2
            else:
                units += 1
        if not supplementary:
            self._map = None
            return
        mapping = [0] * (units + 1)
        u16 = 0
        for index, ch in enumerate(text):
            mapping[u16] = index
            if ord(ch) > 0xFFFF:
                mapping[u16 + 1] = index
                u16 += 2
            else:
                u16 += 1
        mapping[u16] = len(text)
        self._map = mapping

    def _ignored(self, bi) -> bool:
        if not self.skips:
            return False
        rule = bi.getRuleStatus()
        for low, high in self.skips:
            if low <= rule < high:
                return True
        return False

    def spans(self, text: str) -> list[tuple[int, int]]:
        """Code-point spans ``[start, end)`` that the break iterator keeps."""
        if text == "":
            return []
        self._prepare_map(text)
        bi = self.iterator()
        bi.setText(text)
        last = bi.first()
        found = []
        while True:
            pos = bi.nextBoundary()
            if pos == _DONE:
                return found
            if not self._ignored(bi):
                found.append((self._code_points(text, last), self._code_points(text, pos)))
            last = pos


def _engine(opts_brkiter, kwargs) -> _Engine:
    return _Engine(_merge_opts(opts_brkiter, kwargs))


def _no_match_row(get_length: bool):
    if get_length:
        return [-1, -1]
    return [NA, NA]


def _row_from_span(span: tuple[int, int] | None, get_length: bool, missing: bool):
    if missing:
        return [NA, NA]
    if span is None:
        return _no_match_row(get_length)
    start, end = span
    if get_length:
        return [start + 1, end - start]
    return [start + 1, end]


def stri_count_boundaries(str, opts_brkiter=None, **kwargs):
    """Count text-boundary segments in each string.

    The default break iterator is the line breaker. A missing string is
    ``NA``. An empty string counts as 0.
    """
    texts = _as_strings(str)
    engine = _engine(opts_brkiter, kwargs) if texts else None
    out = []
    for text in texts:
        if is_na(text):
            out.append(NA)
        else:
            out.append(len(engine.spans(text)))
    return out


def stri_count_words(str, locale=None):
    """Count words, ignoring ICU ``UBRK_WORD_NONE`` segments."""
    return stri_count_boundaries(
        str,
        opts_brkiter=stri_opts_brkiter(type="word", skip_word_none=True, locale=locale),
    )


def stri_extract_first_boundaries(str, opts_brkiter=None, **kwargs):
    """Return the first boundary segment in each string, or ``NA``."""
    texts = _as_strings(str)
    engine = _engine(opts_brkiter, kwargs) if texts else None
    out = []
    for text in texts:
        if is_na(text) or text == "":
            out.append(NA)
            continue
        spans = engine.spans(text)
        out.append(NA if not spans else text[spans[0][0] : spans[0][1]])
    return out


def stri_extract_last_boundaries(str, opts_brkiter=None, **kwargs):
    """Return the last boundary segment in each string, or ``NA``."""
    texts = _as_strings(str)
    engine = _engine(opts_brkiter, kwargs) if texts else None
    out = []
    for text in texts:
        if is_na(text) or text == "":
            out.append(NA)
            continue
        spans = engine.spans(text)
        out.append(NA if not spans else text[spans[-1][0] : spans[-1][1]])
    return out


def stri_extract_all_boundaries(str, simplify=False, omit_no_match=False, opts_brkiter=None, **kwargs):
    """Return every boundary segment.

    The default is a list of character vectors. No match is a one-element
    ``NA`` vector unless ``omit_no_match`` is true. A missing string stays
    a one-element ``NA`` vector. ``simplify=True`` pads a character matrix
    with empty strings. ``simplify`` missing pads with ``NA``.
    """
    omit = bool(_one_logical(omit_no_match, "omit_no_match", False))
    simple = _one_logical(simplify, "simplify", True)
    texts = _as_strings(str)
    engine = _engine(opts_brkiter, kwargs) if texts else None
    columns = []
    for text in texts:
        if is_na(text):
            columns.append([NA])
            continue
        spans = engine.spans(text)
        if not spans:
            columns.append([] if omit else [NA])
        else:
            columns.append([text[start:end] for start, end in spans])
    if simple is False:
        return columns
    fill = NA if is_na(simple) else ""
    return _list2matrix(columns, fill, 0)


def stri_extract_all_words(str, simplify=False, omit_no_match=False, locale=None):
    """Extract words, ignoring non-word boundary segments."""
    return stri_extract_all_boundaries(
        str,
        simplify=simplify,
        omit_no_match=omit_no_match,
        opts_brkiter=stri_opts_brkiter(type="word", skip_word_none=True, locale=locale),
    )


def stri_extract_first_words(str, locale=None):
    """Return the first word in each string, or ``NA``."""
    return stri_extract_first_boundaries(
        str,
        opts_brkiter=stri_opts_brkiter(type="word", skip_word_none=True, locale=locale),
    )


def stri_extract_last_words(str, locale=None):
    """Return the last word in each string, or ``NA``."""
    return stri_extract_last_boundaries(
        str,
        opts_brkiter=stri_opts_brkiter(type="word", skip_word_none=True, locale=locale),
    )


def stri_locate_first_boundaries(str, get_length=False, opts_brkiter=None, **kwargs):
    """Locate the first boundary segment.

    Each row is ``start``, ``end``. Both are 1-based and inclusive. A miss
    on a real string is ``NA``, ``NA``. With ``get_length=True`` the second
    column is the length, and a miss on a real string is ``-1``, ``-1``.
    A missing string stays ``NA``, ``NA``.
    """
    length_mode = bool(_one_logical(get_length, "get_length", False))
    texts = _as_strings(str)
    engine = _engine(opts_brkiter, kwargs) if texts else None
    rows = []
    for text in texts:
        if is_na(text):
            rows.append([NA, NA])
            continue
        spans = engine.spans(text)
        rows.append(_row_from_span(spans[0] if spans else None, length_mode, False))
    return rows


def stri_locate_last_boundaries(str, get_length=False, opts_brkiter=None, **kwargs):
    """Locate the last boundary segment. Columns follow ``get_length``."""
    length_mode = bool(_one_logical(get_length, "get_length", False))
    texts = _as_strings(str)
    engine = _engine(opts_brkiter, kwargs) if texts else None
    rows = []
    for text in texts:
        if is_na(text):
            rows.append([NA, NA])
            continue
        spans = engine.spans(text)
        rows.append(_row_from_span(spans[-1] if spans else None, length_mode, False))
    return rows


def stri_locate_all_boundaries(
    str, omit_no_match=False, get_length=False, opts_brkiter=None, **kwargs
):
    """Locate every boundary segment.

    The result is a list of matrices. Each matrix has columns ``start`` and
    ``end``, or ``start`` and ``length`` when ``get_length`` is true. A miss
    on a real string is one ``NA`` row, or ``-1``, ``-1`` when ``get_length``
    is true. ``omit_no_match=True`` makes that matrix empty. A missing string
    is one ``NA`` row.
    """
    omit = bool(_one_logical(omit_no_match, "omit_no_match", False))
    length_mode = bool(_one_logical(get_length, "get_length", False))
    texts = _as_strings(str)
    engine = _engine(opts_brkiter, kwargs) if texts else None
    matrices = []
    for text in texts:
        if is_na(text):
            matrices.append([[NA, NA]])
            continue
        spans = engine.spans(text)
        if not spans:
            matrices.append([] if omit else [_no_match_row(length_mode)])
        else:
            matrices.append([_row_from_span(span, length_mode, False) for span in spans])
    return matrices


def stri_locate_all_words(str, omit_no_match=False, locale=None, get_length=False):
    """Locate every word. Non-word segments are omitted."""
    return stri_locate_all_boundaries(
        str,
        omit_no_match=omit_no_match,
        get_length=get_length,
        opts_brkiter=stri_opts_brkiter(type="word", skip_word_none=True, locale=locale),
    )


def stri_locate_first_words(str, locale=None, get_length=False):
    """Locate the first word in each string."""
    return stri_locate_first_boundaries(
        str,
        get_length=get_length,
        opts_brkiter=stri_opts_brkiter(type="word", skip_word_none=True, locale=locale),
    )


def stri_locate_last_words(str, locale=None, get_length=False):
    """Locate the last word in each string."""
    return stri_locate_last_boundaries(
        str,
        get_length=get_length,
        opts_brkiter=stri_opts_brkiter(type="word", skip_word_none=True, locale=locale),
    )


def _split_one(text, n_value, tokens_only: bool, engine: _Engine):
    if is_na(n_value) or is_na(text):
        return [NA]
    if n_value >= _INT_MAX - 1:
        raise ValueError("incorrect argument `n`; value too large")
    if n_value == 0:
        return []
    spans = engine.spans(text)
    if n_value < 0:
        limit = None
    else:
        limit = n_value
    taken = []
    for span in spans:
        if limit is not None and len(taken) >= limit:
            break
        taken.append(span)
    if not taken:
        return []
    if limit is not None and len(taken) == limit and not tokens_only:
        start, _end = taken[-1]
        taken[-1] = (start, len(text))
    return [text[start:end] for start, end in taken]


def stri_split_boundaries(
    str, n=-1, tokens_only=False, simplify=False, opts_brkiter=None, **kwargs
):
    """Split each string at text boundaries.

    ``n`` below 0 returns every piece. A positive ``n`` returns ``n - 1``
    pieces and the unsplit remainder, unless ``tokens_only`` is true, which
    keeps at most ``n`` whole pieces. ``n`` of 0 is an empty vector. A missing
    string or a missing ``n`` is a one-element ``NA`` vector. No boundaries
    yield an empty vector. ``simplify=True`` pads with empty strings and
    ``simplify`` missing pads with ``NA``. The width is at least the largest
    positive ``n``.
    """
    tokens = bool(_one_logical(tokens_only, "tokens_only", False))
    simple = _one_logical(simplify, "simplify", True)
    texts = _as_strings(str)
    counts = _as_ints(n, "n")
    size = _recycle_size([len(texts), len(counts)])
    engine = _engine(opts_brkiter, kwargs) if size else None
    columns = []
    for i in range(size):
        columns.append(_split_one(_at(texts, i), _at(counts, i), tokens, engine))
    if simple is False:
        return columns
    n_min = 0
    for count in counts:
        if not is_na(count) and n_min < count:
            n_min = count
    fill = NA if is_na(simple) else ""
    return _list2matrix(columns, fill, n_min)


def _line_pieces(text: str, omit_empty: bool, lines1: bool) -> list[str]:
    n = len(text)
    i = 0
    start = 0
    pieces: list[str] = []
    while i < n:
        ch = text[i]
        if ch not in _NEWLINES:
            i += 1
            continue
        end = i
        i += 1
        if ch == "\r" and i < n and text[i] == "\n":
            i += 1
        if lines1:
            pieces.append(text[start:end])
            if i >= n:
                return pieces
            start = i
            continue
        if omit_empty and start == end:
            start = i
            continue
        pieces.append(text[start:end])
        start = i
    if lines1:
        if start < n or not pieces:
            pieces.append(text[start:n])
        return pieces
    if omit_empty and start == n:
        return pieces
    pieces.append(text[start:n])
    return pieces


def stri_split_lines(str, omit_empty=False):
    """Split each string on Unicode newline sequences.

    Newlines are CR, LF, CRLF, NEL, VT, FF, line separator, and paragraph
    separator. ``omit_empty=True`` drops empty pieces. ``NA`` is truthy, so
    it drops them too. A missing string becomes a one-element ``NA`` vector.
    """
    texts = _as_strings(str)
    flags = _as_logicals(omit_empty, "omit_empty")
    size = _recycle_size([len(texts), len(flags)])
    out = []
    for i in range(size):
        text = _at(texts, i)
        if is_na(text):
            out.append([NA])
            continue
        out.append(_line_pieces(text, bool(_at(flags, i)), False))
    return out


def stri_split_lines1(str):
    """Split one string into lines and drop a final empty line.

    A trailing newline does not add an empty field. An empty line before
    that trailing newline is kept. A longer character vector warns and uses
    the first element. An empty vector is an error. A missing string is a
    one-element ``NA`` vector.
    """
    if str is None:
        raise ValueError("argument `str` should be a non-empty vector")
    if is_na(str):
        return [NA]
    if isinstance(str, _TEXT):
        text = str
    elif isinstance(str, (list, tuple)):
        if len(str) == 0:
            raise ValueError("argument `str` should be a non-empty vector")
        if len(str) > 1:
            warnings.warn(
                "argument `str` should be a single character string; only the first element is used",
                stacklevel=2,
            )
        text = str[0]
        if is_na(text):
            return [NA]
        if not isinstance(text, _TEXT):
            raise TypeError("str must be a string or a list of strings")
    else:
        raise TypeError("str must be a string or a list of strings")
    return _line_pieces(text, False, True)
