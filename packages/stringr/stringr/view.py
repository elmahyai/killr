"""Text view of strings and matches.

``html=TRUE`` needs htmltools and htmlwidgets, which are suggested and are
not a dependency of this translation. The text view is the ``html=FALSE``
path: matches are wrapped in ``<>``, and unusual whitespace is wrapped in
``{}``. The spans are the 1-based inclusive locations ``stri_locate_all``
reports, including a zero-width match whose end is one less than its start.
"""

from __future__ import annotations

from typing import Any

from cli import ansi_strsplit, cli_inform, col_cyan, col_grey, col_red, is_utf8_output
from lifecycle import deprecate_warn
from stringi import (
    stri_escape_unicode,
    stri_locate_all_boundaries,
    stri_locate_all_coll,
    stri_locate_all_fixed,
    stri_locate_all_regex,
)
from stringi._na import NA, is_na
from vctrs import vec_recycle_common

from stringr._size import no_empty
from stringr.pattern import Pattern, as_strings, pattern_opts, pattern_type


class StringrView(list):
    """A character vector of highlighted strings, with the original positions.

    ``ids`` are 1-based indexes into the input. ``spans`` are the match
    locations in those strings, each ``[start, end]`` inclusive. A zero-width
    match has ``end < start``.
    """

    def __init__(self, values: list, ids: list[int], spans: list[list[list[int]]]) -> None:
        super().__init__(values)
        self.ids = ids
        self.spans = spans

    def __str__(self) -> str:
        return format_view(self)


def _check_bool(value: object, allow_na: bool = False) -> None:
    if value is True or value is False:
        return
    if allow_na and is_na(value):
        return
    raise ValueError("`TRUE` or `FALSE` is required.")


def _characters(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, str) or is_na(value):
        return [value]
    if isinstance(value, (list, tuple)):
        return list(value)
    raise TypeError("string must be a character vector.")


def _recycle(string: Any, pattern: Any) -> tuple[list, Any, str | None, dict | None]:
    """Recycle ``string`` and ``pattern`` the way ``vec_recycle_common`` does.

    ``pattern is None`` is R's ``NULL``. The translated recycler treats
    ``None`` as a length-1 vector, so a missing pattern is left out of that
    call and stays missing.
    """

    strings = _characters(string)
    if pattern is None:
        return strings, None, None, None
    kind = pattern_type(pattern)
    opts = pattern_opts(pattern)
    values = as_strings(pattern)
    recycled = vec_recycle_common(strings, values)
    strings, values = recycled
    if isinstance(pattern, Pattern):
        values = Pattern(values, pattern.options, pattern.kind)
    return strings, values, kind, opts


def _locate_all(strings: list, values: Any, kind: str, opts: dict | None) -> list:
    if kind in ("empty", "bound"):
        return stri_locate_all_boundaries(strings, omit_no_match=True, opts_brkiter=opts)
    pattern = as_strings(values)
    if kind == "fixed":
        return stri_locate_all_fixed(strings, pattern, omit_no_match=True, opts_fixed=opts)
    if kind == "coll":
        return stri_locate_all_coll(strings, pattern, omit_no_match=True, opts_collator=opts)
    return stri_locate_all_regex(strings, pattern, omit_no_match=True, opts_regex=opts)


def _spans_of(rows: list) -> list[list[int]]:
    spans = []
    for row in rows:
        if not row or len(row) < 2:
            continue
        start, end = row[0], row[1]
        if is_na(start) or is_na(end):
            continue
        spans.append([int(start), int(end)])
    return spans


def _has_match(rows: list) -> bool:
    return bool(_spans_of(rows))


def _piece(text: str, start: int, end: int) -> str:
    if end >= start:
        return text[start - 1 : end]
    return ""


def _wrap_match(piece: str) -> str:
    colored = col_cyan("<", piece, ">")
    parts = ansi_strsplit(colored, "\n", fixed=True)
    if isinstance(parts, str):
        return parts
    return "\n".join("" if part is None else str(part) for part in parts)


def _splice(text: str, spans: list[list[int]], replacements: list[str]) -> str:
    parts: list[str] = []
    cursor = 0
    for (start, end), replacement in zip(spans, replacements):
        insert_at = start - 1
        if insert_at < cursor:
            insert_at = cursor
        if insert_at > cursor:
            parts.append(text[cursor:insert_at])
        parts.append(replacement)
        if end >= start:
            cursor = end
        else:
            cursor = insert_at
    parts.append(text[cursor:])
    return "".join(parts)


def _highlight(text: Any, spans: list[list[int]]) -> Any:
    if is_na(text) or not spans:
        return text
    replacements = [_wrap_match(_piece(text, start, end)) for start, end in spans]
    return _splice(text, spans, replacements)


def _special(text: Any) -> Any:
    """Wrap unusual whitespace in ``{}`` and escape it."""

    if is_na(text) or text == "":
        return text
    rows = stri_locate_all_regex(text, r"[\p{Whitespace}-- \n]+", omit_no_match=True)[0]
    spans = _spans_of(rows)
    if not spans:
        return text
    pieces = [_piece(text, start, end) for start, end in spans]
    escaped = stri_escape_unicode(pieces)
    replacements = []
    for item in escaped:
        colored = col_cyan("{", item, "}")
        replacements.append("" if colored is None else str(colored))
    return _splice(text, spans, replacements)


def _escape_keep_ansi(values: list) -> list:
    escaped = stri_escape_unicode(values)
    out = []
    for item in escaped:
        if is_na(item):
            out.append(NA)
        else:
            out.append(item.replace("\\u001b", "\u001b"))
    return out


def format_view(view: StringrView, n: int = 20) -> str:
    """The ``html=FALSE`` print: a grey index, a bar, and the highlighted text."""

    if len(view) == 0:
        cli_inform({"x": "Empty `string` provided.\n"})
        return ""
    extra = len(view) - n
    if extra > 0:
        shown = list(view)[:n]
        ids = view.ids[:n]
    else:
        shown = list(view)
        ids = list(view.ids)
        extra = 0
    bar = "\u2502" if is_utf8_output() else "|"
    labels = [f"[{index}] " for index in ids]
    width = max(len(label) for label in labels)
    labels = [label.rjust(width) for label in labels]
    pad = " " * len(labels[0])
    exdent = pad + str(col_grey(bar)) + " "
    lines = []
    for label, text in zip(labels, shown):
        body = col_red("NA") if is_na(text) else text
        indent = str(col_grey(label, bar)) + " "
        rendered = str(body).replace("\n", "\n" + exdent)
        lines.append(indent + rendered)
    formatted = "\n".join(lines)
    if extra > 0:
        formatted += f"\n... and {extra} more"
    return formatted


def str_view(
    string: Any,
    pattern: Any = None,
    match: Any = True,
    html: bool = False,
    use_escapes: bool = False,
) -> StringrView:
    """Show strings, and wrap each match of ``pattern`` in ``<>``.

    ``match=True`` keeps elements that match. ``match=False`` keeps the
    others, including missing strings. ``NA`` keeps every element. A missing
    pattern shows every element and only marks unusual whitespace.
    ``html=True`` is not available: it needs htmltools and htmlwidgets.
    """

    strings, values, kind, opts = _recycle(string, pattern)
    _check_bool(match, allow_na=True)
    _check_bool(html)
    _check_bool(use_escapes)
    if html:
        raise RuntimeError(
            "html=TRUE needs htmltools and htmlwidgets, which are not installed."
        )
    if kind == "empty":
        no_empty()

    if kind is None:
        located = [[] for _ in strings]
        mask = [True] * len(strings)
    elif kind == "bound":
        located = _locate_all(strings, values, kind, opts)
        mask = [True] * len(strings)
    else:
        located = _locate_all(strings, values, kind, opts)
        detected = [None if is_na(text) else _has_match(rows) for text, rows in zip(strings, located)]
        if match is True:
            mask = [hit is True for hit in detected]
        elif match is False:
            mask = [hit is not True for hit in detected]
        else:
            mask = [True] * len(strings)

    shown = [text for text, keep in zip(strings, mask) if keep]
    shown_rows = [rows for rows, keep in zip(located, mask) if keep]
    ids = [index + 1 for index, keep in enumerate(mask) if keep]
    spans = [_spans_of(rows) for rows in shown_rows]
    if kind is None:
        highlighted = list(shown)
        spans = [[] for _ in shown]
    else:
        highlighted = [_highlight(text, one) for text, one in zip(shown, spans)]
    if use_escapes:
        highlighted = _escape_keep_ansi(highlighted)
    else:
        highlighted = [_special(text) for text in highlighted]
    return StringrView(highlighted, ids, spans)


def str_view_all(
    string: Any,
    pattern: Any = None,
    match: Any = NA,
    html: bool = False,
    use_escapes: bool = False,
) -> StringrView:
    """Deprecated alias of ``str_view``. The default ``match`` is ``NA``."""

    deprecate_warn("1.5.0", "str_view_all()", "str_view()", package="stringr")
    return str_view(string, pattern=pattern, match=match, html=html, use_escapes=use_escapes)
