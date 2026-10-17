"""Rules, alignment, trimming, and column layout.

These follow the R functions once ansi_substr can keep styles.
"""

from __future__ import annotations

import math
import re
import sys

from cli._options import get_option
from cli.ansi_text import (
    ansi_nchar,
    ansi_strip,
    ansi_substr,
    ansi_substring,
)
from cli.styles import make_ansi_style
from cli.symbol import symbol
from cli.utf8 import _as_text, _match_arg, _scalar, _vector


def console_width() -> int:
    """Character width of the console. cli.width wins, otherwise 80."""

    chosen = get_option("cli.width")
    if chosen is not None:
        if isinstance(chosen, bool) or not isinstance(chosen, (int, float)):
            raise ValueError("options('cli.width') must be an integer scalar")
        if isinstance(chosen, float) and math.isnan(chosen):
            raise ValueError("options('cli.width') cannot be NA")
        if chosen == math.inf:
            return sys.maxsize
        value = int(chosen)
        if value <= 0:
            raise ValueError("options('cli.width') must be a positive integer")
        return value
    width = get_option("width", 80)
    if width is None:
        return 80
    return int(width)


def _apply_style(text, style, bg: bool = False):
    if text == "":
        return text
    if style is None:
        return text
    if isinstance(text, (list, tuple)):
        return [_apply_style(item, style, bg=bg) for item in text]
    if callable(style):
        return style(text)
    if isinstance(style, str):
        return make_ansi_style(style, bg=bg)(text)
    raise TypeError("style must be a color name or an ANSI style function")


def _spaces(count) -> str:
    if isinstance(count, float) and math.isnan(count):
        return ""
    count = math.trunc(count)
    if count <= 0:
        return ""
    return " " * count


def _line_char(line) -> str:
    if line in (1, 1.0, "single"):
        return symbol["line"]
    if line in (2, 2.0, "double"):
        return symbol["double_line"]
    if isinstance(line, str) and line in {f"bar{i}" for i in range(1, 9)}:
        return symbol[f"lower_block_{line[-1]}"]
    return "" if line is None else str(line)


def _make_line(count, char, col) -> str:
    if count <= 0:
        return ""
    width = ansi_nchar(char, "width") or 1
    if width == 1:
        line = char * int(count)
    else:
        copies = math.ceil(count / width)
        line = ansi_substr(char * copies, 1, int(count))
    return _apply_style(line, col)


def rule(
    left="",
    center="",
    right="",
    line=1,
    col=None,
    line_col=None,
    background_col=None,
    width=None,
):
    """A rule with an optional left, center, or right label."""

    if width is None:
        width = console_width()
    if line_col is None:
        line_col = col
    width = int(width)
    left = _apply_style("" if left is None else str(left), col)
    center = _apply_style("" if center is None else str(center), col)
    right = _apply_style("" if right is None else str(right), col)
    glyph = _line_char(line)
    if ansi_nchar(center):
        if ansi_nchar(left) or ansi_nchar(right):
            raise ValueError("center cannot be specified with left or right")
        center = ansi_substring(center, 1, width - 4)
        center = f" {center} "
        dashes = width - ansi_nchar(center, "width")
        text = (
            _make_line(math.ceil(dashes / 2), glyph, line_col)
            + center
            + _make_line(math.floor(dashes / 2), glyph, line_col)
        )
    elif ansi_nchar(left) and ansi_nchar(right):
        ncl = ansi_nchar(left, "width")
        ncr = ansi_nchar(right, "width")
        if ncl + ncr + 10 > width:
            text = _rule_left(left, glyph, line_col, width)
        else:
            text = (
                _make_line(2, glyph, line_col)
                + f" {left} "
                + _make_line(width - ncl - ncr - 8, glyph, line_col)
                + f" {right} "
                + _make_line(2, glyph, line_col)
            )
    elif ansi_nchar(left):
        text = _rule_left(left, glyph, line_col, width)
    elif ansi_nchar(right):
        ncr = ansi_nchar(right, "width")
        text = (
            _make_line(width - ncr - 4, glyph, line_col)
            + f" {right} "
            + _make_line(2, glyph, line_col)
        )
    else:
        text = _make_line(width, glyph, line_col)
    text = ansi_substr(text, 1, width)
    return _apply_style(text, background_col, bg=True)


def _rule_left(left, glyph, line_col, width) -> str:
    ncl = ansi_nchar(left, "width")
    return (
        _make_line(2, glyph, line_col)
        + f" {left} "
        + _make_line(width - ncl - 4, glyph, line_col)
    )


def ansi_align(text, width=None, align="left", type="width"):
    """Pad a string on the left, right, or both sides."""

    if width is None:
        width = console_width()
    align = _match_arg(align, ("left", "center", "right"))
    values = _vector(text)
    if isinstance(text, (list, tuple)) and not values:
        return []
    measured = ansi_nchar(values, type)
    if not isinstance(measured, list):
        measured = [measured]
    out = []
    for item, count in zip(values, measured):
        if item is None or count is None:
            out.append(None)
            continue
        gap = width - count
        if align == "left":
            out.append(f"{item}{_spaces(gap)}")
        elif align == "right":
            out.append(f"{_spaces(gap)}{item}")
        else:
            out.append(f"{_spaces(math.ceil(gap / 2))}{item}{_spaces(math.floor(gap / 2))}")
    return _scalar(text, out)


_WS = set(" \t\n\r\f\v")


def _trim_count(text: str, which: str) -> tuple[int, int]:
    left = 0
    if which in ("both", "left"):
        while left < len(text) and text[left] in _WS:
            left += 1
    right = 0
    if which in ("both", "right"):
        end = len(text)
        while end > left and text[end - 1] in _WS:
            right += 1
            end -= 1
    return left, right


def ansi_trimws(x, which="both"):
    """Trim whitespace without dropping ANSI styles."""

    which = _match_arg(which, ("both", "left", "right"))
    values = _vector(x)
    if isinstance(x, (list, tuple)) and not values:
        return []
    out = []
    for value in values:
        text = _as_text(value)
        if text is None:
            out.append(None)
            continue
        left, right = _trim_count(ansi_strip(text), which)
        if left or right:
            out.append(ansi_substr(text, 1 + left, ansi_nchar(text) - right))
        else:
            out.append(text)
    return _scalar(x, out)


def ansi_nzchar(x):
    """Whether the visible text is non-empty."""

    stripped = ansi_strip(x)
    values = stripped if isinstance(stripped, list) else [stripped]
    out = []
    for item in values:
        if item is None:
            out.append(None)
        else:
            out.append(len(item) > 0)
    return _scalar(x, out)


def ansi_strtrim(x, width=None, ellipsis=None):
    """Truncate to a display width and mark the cut with an ellipsis."""

    if width is None:
        width = console_width()
    if width < 0:
        raise ValueError("width must be non-negative")
    if ellipsis is None:
        ellipsis = symbol["ellipsis"]
    ellipsis = "" if ellipsis is None else str(ellipsis)
    tw = ansi_nchar(ellipsis, "width")
    values = _vector(x)
    if tw == width:
        return _scalar(x, [ellipsis for _ in values])
    if tw > width:
        shortened = ansi_strtrim(ellipsis, width, ellipsis="")
        return _scalar(x, [shortened for _ in values])
    trimmed = []
    for value in values:
        text = _as_text(value)
        trimmed.append(None if text is None else ansi_substr(text, 1, int(width)))
    bad0 = []
    for original, piece in zip(values, trimmed):
        if piece is None or original is None:
            bad0.append(False)
            continue
        if ansi_nzchar(ellipsis):
            bad0.append(ansi_strip(piece) != ansi_strip(original) or ansi_nchar(piece, "width") > width)
        else:
            bad0.append(ansi_nchar(piece, "width") > width)
    current = list(trimmed)
    guard = 0
    while any(
        piece is not None and ansi_nchar(piece, "width") > width - tw
        for piece, flag in zip(current, bad0)
        if flag
    ):
        guard += 1
        if guard > 10000:
            break
        for index, flag in enumerate(bad0):
            if not flag or current[index] is None:
                continue
            if ansi_nchar(current[index], "width") > width - tw:
                length = ansi_nchar(current[index])
                current[index] = ansi_substr(current[index], 1, length - 1)
    out = []
    for piece, flag in zip(current, bad0):
        if piece is None:
            out.append(None)
        elif flag:
            out.append(piece + ellipsis)
        else:
            out.append(piece)
    return _scalar(x, out)


def _convert_visible(text: str, fn) -> str:
    pieces = []
    from cli.ansi_text import _walk

    for event in _walk(text):
        if event[0] == "text":
            pieces.append(fn(event[1]))
        elif event[0] == "link":
            pieces.append(event[4])
        else:
            pieces.append(event[2])
    return "".join(pieces)


def ansi_toupper(x):
    """Upper case, leaving ANSI sequences unchanged."""

    return _map_visible(x, str.upper)


def ansi_tolower(x):
    """Lower case, leaving ANSI sequences unchanged."""

    return _map_visible(x, str.lower)


def ansi_chartr(old, new, x):
    """Translate characters, leaving ANSI sequences unchanged."""

    old = "" if old is None else str(old)
    new = "" if new is None else str(new)
    if len(old) != len(new):
        raise ValueError("old and new must have the same number of characters")
    table = str.maketrans(old, new)
    return _map_visible(x, lambda text: text.translate(table))


def _map_visible(x, fn):
    out = []
    for value in _vector(x):
        text = _as_text(value)
        out.append(None if text is None else _convert_visible(text, fn))
    return _scalar(x, out)


def _search(pattern: str, text: str, ignore_case: bool, fixed: bool):
    if text is None:
        return None
    flags = re.IGNORECASE if ignore_case else 0
    if fixed:
        pattern = re.escape(pattern)
    return re.search(pattern, text, flags) is not None


def ansi_grepl(pattern, x, ignore_case=False, fixed=False):
    """Whether the visible text matches. Styles are stripped first."""

    needle = ansi_strip(pattern)
    if isinstance(needle, list):
        needle = needle[0] if needle else ""
    needle = "" if needle is None else needle
    out = []
    for value in _vector(x):
        text = ansi_strip(value)
        out.append(_search(needle, text, ignore_case, fixed))
    return _scalar(x, out)


def ansi_grep(pattern, x, ignore_case=False, fixed=False, value=False):
    """1-based indexes of visible matches, or the matching stripped strings."""

    hits = ansi_grepl(pattern, x, ignore_case=ignore_case, fixed=fixed)
    values = _vector(x)
    flags = hits if isinstance(hits, list) else [hits]
    stripped = [ansi_strip(item) for item in values]
    chosen = []
    indexes = []
    for index, flag in enumerate(flags, start=1):
        if flag:
            indexes.append(index)
            chosen.append(stripped[index - 1])
    if value:
        return chosen
    return indexes


def ansi_columns(
    text,
    width=None,
    sep=" ",
    fill="rows",
    max_cols=4,
    align="left",
    type="width",
    ellipsis=None,
):
    """Lay text out in columns. Cells that do not fit are trimmed."""

    if width is None:
        width = console_width()
    fill = _match_arg(fill, ("rows", "cols"))
    align = _match_arg(align, ("left", "center", "right"))
    values = _vector(text)
    if not values:
        return []
    sep_width = ansi_nchar(sep, "width")
    widest = max(ansi_nchar(values, type)) + sep_width
    cols = min(math.floor(width / widest) if widest else 1, max_cols)
    if cols <= 0:
        cols = 1
        values = _vector(ansi_strtrim(values, width=width, ellipsis=ellipsis))
    extra = math.ceil(len(values) / cols) * cols - len(values)
    values = values + [""] * extra
    rows = math.ceil(len(values) / cols)
    if fill == "rows":
        grid = [values[i * cols : (i + 1) * cols] for i in range(rows)]
    else:
        grid = [[values[row + col * rows] for col in range(cols)] for row in range(rows)]
    spans = []
    for col in range(1, cols + 1):
        spans.append(round((width / cols) * col) - round((width / cols) * (col - 1)))
    lines = []
    for row in grid:
        cells = []
        for col, cell in enumerate(row):
            shown = f"{cell}{sep}" if cols > 1 else cell
            cells.append(ansi_align(shown, spans[col], align=align, type=type))
        lines.append("".join(cells))
    return lines


def ruler(width=None):
    """Print a column ruler. Returns the printed text."""

    if width is None:
        width = console_width()
    marks = []
    digits = []
    for pos in range(1, int(width) + 1):
        if pos % 10 == 0:
            digit = str((pos // 10) % 10)
            marks.append(make_ansi_style("bold")(digit))
        elif pos % 5 == 0:
            marks.append("+")
        else:
            marks.append("-")
        digits.append(str(pos % 10))
    text = "".join(marks) + "\n" + "".join(digits) + "\n"
    sys.stdout.write(text)
    return text
