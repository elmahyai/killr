"""Print UTF-8 text in columns, after formatting it."""

from __future__ import annotations

import sys
from typing import Any

from utf8._text import display_width
from utf8.utf8_format import utf8_format

_LINE_WIDTH = 80


def _pad(text: str, field: int, right: bool) -> str:
    width = display_width(text) or 0
    gap = max(0, field - width)
    if right:
        return (" " * gap) + text
    return text + (" " * gap)


def _quoted(text: str) -> str:
    return f'"{text}"'


def utf8_print(
    x: Any,
    *,
    chars: int | None = None,
    quote: bool = True,
    right: bool = False,
    max_print: int | None = None,
    line_width: int = _LINE_WIDTH,
    file: Any = None,
) -> Any:
    """Format ``x`` and print it. The same object is returned."""

    if x is None:
        return None
    if isinstance(x, str):
        values = [x]
        names = None
    elif isinstance(x, dict):
        names = list(x)
        values = [x[name] for name in names]
    else:
        values = list(x)
        names = None
    formatted = [
        utf8_format(value, trim=True, chars=chars, justify="right" if right else "left")
        for value in values
    ]
    limit = len(formatted) if max_print is None else max_print
    shown = formatted[:limit]
    out = file if file is not None else sys.stdout
    if names is None:
        _print_unnamed(shown, quote, line_width, out)
    else:
        _print_named(shown, names[:limit], quote, line_width, out)
    if limit < len(formatted):
        print(
            f' [ reached max.print -- omitted {len(formatted) - limit} entries ]',
            file=out,
        )
    return x


def _print_named(values: list[str], names: list[str], quote: bool, line_width: int, out: Any) -> None:
    cells = [_quoted(value) if quote else value for value in values]
    field = max([*(display_width(cell) or 0 for cell in cells), *(display_width(name) or 0 for name in names), 0])
    gap = 1
    per = field + gap
    columns = max(1, line_width // per)
    for start in range(0, len(cells), columns):
        group_cells = cells[start : start + columns]
        group_names = names[start : start + columns]
        print(" ".join(_pad(name, field, False) for name in group_names), file=out)
        print(" ".join(_pad(cell, field, False) for cell in group_cells), file=out)


def _print_unnamed(values: list[str], quote: bool, line_width: int, out: Any) -> None:
    cells = [_quoted(value) if quote else value for value in values]
    if not cells:
        print("character(0)", file=out)
        return
    labels = [f"[{index}]" for index in range(1, len(cells) + 1)]
    label_width = max(display_width(label) or 0 for label in labels)
    field = max(display_width(cell) or 0 for cell in cells)
    columns = max(1, (line_width - label_width) // (field + 1))
    rows = []
    for start in range(0, len(cells), columns):
        group = cells[start : start + columns]
        label = labels[start]
        body = " ".join(_pad(cell, field, False) for cell in group)
        rows.append(f"{label.rjust(label_width)} {body}")
    print("\n".join(rows), file=out)
