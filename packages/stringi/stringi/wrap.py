"""Word wrap using ICU line breaks and stringi's width.

The greedy and dynamic algorithms are the ones in ``stri_wrap.cpp``.
Width of a word is ``stri_width``. A missing string stays missing.
``normalize=True`` flattens line breaks, merges ASCII spaces, trims, and
applies NFC before wrapping.
"""

from __future__ import annotations

import math
import re
import warnings

import icu

from stringi._na import NA
from stringi.join import (
    _prepare_integer,
    _prepare_logical_1,
    _prepare_string,
    _prepare_string_1,
    stri_flatten,
)
from stringi.length import stri_width
from stringi.locale import _as_one_string
from stringi.normalize import stri_trans_nfc

_NOT_GIVEN = object()
_LINEBREAKS = frozenset({0x0A, 0x0B, 0x0C, 0x0D, 0x85, 0x2028, 0x2029})
_ASCII_GAP = re.compile(r"[ \r\n\t]+")


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=3)


def _one_integer(value, name: str) -> int:
    values = _prepare_integer(value, name)
    if len(values) == 0:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    if len(values) > 1:
        _warn(
            f"argument `{name}` should be a single integer value; "
            "only the first element is used"
        )
    if values[0] is NA:
        raise ValueError(f"missing values in argument `{name}` is not supported")
    return values[0]


def _one_double(value, name: str) -> float:
    if value is None:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            _warn(
                f"argument `{name}` should be a single numeric value; "
                "only the first element is used"
            )
        value = value[0]
    if value is NA:
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            raise ValueError(f"missing values in argument `{name}` is not supported")
        return float(value)
    raise ValueError(
        f"argument `{name}` should be a numeric vector (or an object coercible to)"
    )


def _split_lines(text: str) -> list:
    parts = []
    start = 0
    index = 0
    size = len(text)
    while index < size:
        code = ord(text[index])
        if code not in (0x0A, 0x0B, 0x0C, 0x0D, 0x85, 0x2028, 0x2029):
            index += 1
            continue
        parts.append(text[start:index])
        index += 1
        if code == 0x0D and index < size and text[index] == "\n":
            index += 1
        start = index
    if start < size or not parts:
        parts.append(text[start:])
    return parts


def _white(code: int) -> bool:
    return icu.Char.hasBinaryProperty(code, icu.UProperty.WHITE_SPACE)


def _trim(text: str) -> str:
    start = 0
    end = len(text)
    while start < end and _white(ord(text[start])):
        start += 1
    while end > start and _white(ord(text[end - 1])):
        end -= 1
    return text[start:end]


def _normalize(strings: list) -> list:
    normalized = []
    for text in strings:
        if text is NA:
            normalized.append(NA)
            continue
        lines = _split_lines(text)
        flat = stri_flatten(lines, collapse=" ")
        merged = _ASCII_GAP.sub(" ", flat[0] if flat[0] is not NA else "")
        if flat[0] is NA:
            normalized.append(NA)
            continue
        normalized.append(stri_trans_nfc(_trim(merged)))
    return normalized


def _utf16_to_python(text: str) -> dict:
    mapping = {}
    unit = 0
    for index, char in enumerate(text):
        mapping[unit] = index
        unit += 2 if ord(char) > 0xFFFF else 1
    mapping[unit] = len(text)
    return mapping


def _breaks(text: str, locale: str, whitespace_only: bool) -> list:
    breaker = icu.BreakIterator.createLineInstance(icu.Locale(locale))
    breaker.setText(text)
    mapping = _utf16_to_python(text)
    found = []
    position = breaker.first()
    size = len(text)
    while position != icu.BreakIterator.DONE:
        python_index = mapping.get(position)
        if python_index is None:
            raise ValueError("internal error")
        if not whitespace_only:
            found.append(python_index)
        elif python_index == 0 or python_index == size:
            found.append(python_index)
        elif _white(ord(text[python_index - 1])):
            found.append(python_index)
        position = breaker.nextBoundary()
    return found


def _measure(text: str, use_length: bool):
    if text == "":
        return 0, 0, 0
    if use_length:
        original = len(text)
    else:
        original = stri_width(text)
    if _white(ord(text[-1])):
        trimmed_text = text[:-1]
        if use_length:
            trimmed = len(trimmed_text)
        else:
            trimmed = stri_width(trimmed_text) if trimmed_text else 0
        end = len(trimmed_text)
    else:
        trimmed = original
        end = len(text)
    return original, trimmed, end


def _greedy(nwords, width, widths_orig, widths_trim, add_first, add_next):
    wraps = []
    current = add_first + widths_orig[0]
    for index in range(1, nwords):
        if current + widths_trim[index] > width:
            current = add_next + widths_orig[index]
            wraps.append(index - 1)
        else:
            current += widths_orig[index]
    return wraps


def _dynamic(nwords, width, exponent, widths_orig, widths_trim, add_first, add_next):
    def cell(row, column):
        return row * nwords + column

    cost = [0.0] * (nwords * nwords)
    for start in range(nwords):
        total = 0
        for end in range(start, nwords):
            if end > start:
                if cost[cell(start, end - 1)] < 0.0:
                    cost[cell(start, end)] = -1.0
                    continue
                total -= widths_trim[end - 1]
                total += widths_orig[end - 1]
            total += widths_trim[end]
            slack = width - total
            if start == 0:
                slack -= add_first
            else:
                slack -= add_next
            if end == nwords - 1:
                if end == start or slack >= 0:
                    cost[cell(start, end)] = 0.0
                else:
                    cost[cell(start, end)] = -1.0
            elif end == start:
                cost[cell(start, end)] = 0.0 if slack < 0 else math.pow(float(slack), exponent)
            else:
                cost[cell(start, end)] = -1.0 if slack < 0 else math.pow(float(slack), exponent)

    best = [0.0] * nwords
    where = [False] * (nwords * nwords)
    for end in range(nwords):
        if cost[cell(0, end)] >= 0.0:
            best[end] = cost[cell(0, end)]
            continue
        split = 0
        while split <= end:
            if cost[cell(split + 1, end)] >= 0.0:
                break
            split += 1
        chosen = best[split] + cost[cell(split + 1, end)]
        for candidate in range(split + 1, end):
            if cost[cell(candidate + 1, end)] < 0.0:
                continue
            score = best[candidate] + cost[cell(candidate + 1, end)]
            if score < chosen:
                chosen = score
                split = candidate
        for earlier in range(split):
            where[cell(earlier, end)] = where[cell(earlier, split)]
        where[cell(split, end)] = True
        best[end] = chosen
    return [index for index in range(nwords) if where[cell(index, nwords - 1)]]


def _opening(prefix: str, spaces: int, use_length: bool):
    text = prefix + (" " * spaces)
    if use_length:
        measure = len(prefix) + spaces
    else:
        measure = (stri_width(prefix) if prefix else 0) + spaces
    return text, measure


def stri_wrap(
    str,
    width=72,
    cost_exponent=2,
    simplify=True,
    normalize=True,
    normalise=_NOT_GIVEN,
    indent=0,
    exdent=0,
    prefix="",
    initial=_NOT_GIVEN,
    whitespace_only=False,
    use_length=False,
    locale=None,
):
    """Wrap paragraphs to ``width`` columns.

    ``cost_exponent <= 0`` selects the greedy fit. A positive exponent
    selects Knuth's dynamic program, and the last line costs nothing.
    Breaks come from ICU's line-break iterator unless ``whitespace_only``
    is true. ``use_length`` counts code points instead of ``stri_width``.
    """

    if normalise is not _NOT_GIVEN:
        normalize = normalise
    if initial is _NOT_GIVEN:
        initial = prefix
    do_simplify = _prepare_logical_1(simplify, "simplify", allow_na=False)
    do_normalize = _prepare_logical_1(normalize, "normalize", allow_na=False)
    only_space = _prepare_logical_1(whitespace_only, "whitespace_only", allow_na=False)
    by_length = _prepare_logical_1(use_length, "use_length", allow_na=False)
    exponent = _one_double(cost_exponent, "cost_exponent")
    width_val = _one_integer(width, "width")
    if width_val < 0:
        width_val = 0
    indent_val = _one_integer(indent, "indent")
    if indent_val < 0:
        raise ValueError(
            "incorrect argument `indent`; expected a positive numeric value"
        )
    exdent_val = _one_integer(exdent, "exdent")
    if exdent_val < 0:
        raise ValueError(
            "incorrect argument `exdent`; expected a positive numeric value"
        )
    strings = _prepare_string(str, "str")
    if do_normalize:
        strings = _normalize(strings)
    prefix_text = _prepare_string_1(prefix, "prefix")
    initial_text = _prepare_string_1(initial, "initial")
    locale_name = _as_one_string(locale, allow_default=True)
    wrapped = []
    for paragraph_index, text in enumerate(strings):
        if text is NA or prefix_text is NA or initial_text is NA:
            wrapped.append([NA])
            continue
        for code in map(ord, text):
            if code in _LINEBREAKS:
                raise ValueError("newline character found in a string")
        boundaries = _breaks(text, locale_name, bool(only_space))
        if len(boundaries) <= 1:
            wrapped.append([text])
            continue
        if boundaries[0] != 0:
            raise ValueError("internal error")
        ends = boundaries[1:]
        nwords = len(ends)
        widths_orig = []
        widths_trim = []
        trim_ends = []
        start = 0
        for end in ends:
            word = text[start:end]
            original, trimmed, trim_at = _measure(word, bool(by_length))
            widths_orig.append(original)
            widths_trim.append(trimmed)
            trim_ends.append(start + trim_at)
            start = end
        first_text, first_measure = _opening(
            initial_text if paragraph_index == 0 else prefix_text,
            indent_val,
            bool(by_length),
        )
        next_text, next_measure = _opening(prefix_text, exdent_val, bool(by_length))
        later_first_text, later_first_measure = _opening(
            prefix_text, indent_val, bool(by_length)
        )
        add_first = first_measure if paragraph_index == 0 else later_first_measure
        if exponent <= 0.0:
            wrap_after = _greedy(
                nwords, width_val, widths_orig, widths_trim, add_first, next_measure
            )
        else:
            wrap_after = _dynamic(
                nwords,
                width_val,
                exponent,
                widths_orig,
                widths_trim,
                add_first,
                next_measure,
            )
        lines = []
        last = 0
        for line_index, split in enumerate(wrap_after):
            if paragraph_index == 0 and line_index == 0:
                head = first_text
            elif paragraph_index > 0 and line_index == 0:
                head = later_first_text
            else:
                head = next_text
            lines.append(head + text[last:trim_ends[split]])
            last = ends[split]
        last_index = len(wrap_after)
        if paragraph_index == 0 and last_index == 0:
            head = first_text
        elif paragraph_index > 0 and last_index == 0:
            head = later_first_text
        else:
            head = next_text
        lines.append(head + text[last:trim_ends[-1]])
        wrapped.append(lines)
    if do_simplify:
        flat = []
        for lines in wrapped:
            flat.extend(lines)
        return flat
    return wrapped
