"""Horizontal preview of a data frame.

``format_glimpse()`` renders one element. ``glimpse()`` prints the size and
one line per column. A data frame uses the ``tbl`` method: the first header
line is not repeated, and each column is ``$ name <type> values``.
"""

from __future__ import annotations

from typing import Any

from cli.cat import cat_line

from pillar._layout import big_mark, str_trunc, tick_if_needed, width_print
from pillar._text import is_na, paste_atom
from pillar._vec import NULL, DataFrame, Factor, List
from pillar._width import display_extent
from pillar.parts import new_pillar_title, new_pillar_type
from pillar.styles import style_na, style_subtle


def _encode(text: Any, quote: str = '"') -> Any:
    if text is None or is_na(text):
        return None
    body = str(text)
    body = body.replace("\\", "\\\\").replace(quote, "\\" + quote)
    body = body.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return quote + body + quote


def _style_na_if(values: list[Any], missing: list[bool]) -> list[Any]:
    indexes = [index for index, flag in enumerate(missing) if flag]
    if not indexes:
        return values
    token = style_na(values[indexes[0]])
    out = list(values)
    for index in indexes:
        out[index] = token
    return out


def _atomic(values: list[Any]) -> list[str]:
    out: list[Any] = []
    missing: list[bool] = []
    for item in values:
        if item is None or is_na(item):
            out.append("NA")
            missing.append(True)
        elif isinstance(item, bool):
            out.append("TRUE" if item else "FALSE")
            missing.append(False)
        elif isinstance(item, float):
            if item != item:
                out.append("NaN")
                missing.append(True)
            elif item == float("inf"):
                out.append("Inf")
                missing.append(False)
            elif item == float("-inf"):
                out.append("-Inf")
                missing.append(False)
            else:
                text = format(item, "g")
                out.append(text)
                missing.append(False)
        else:
            out.append(paste_atom(item))
            missing.append(False)
    styled = _style_na_if(out, missing)
    return ["NA" if item is None else str(item) for item in styled]


def _character(values: list[Any]) -> list[Any]:
    encoded = [_encode(item) for item in values]
    missing = [item is None for item in encoded]
    shown = ["NA" if item is None else item for item in encoded]
    return _style_na_if(shown, missing)


def _is_list(value: Any) -> bool:
    return isinstance(value, List) or value is NULL and False


def _length(value: Any) -> int:
    if value is NULL or value is None:
        return 0
    if isinstance(value, List):
        return len(value.items)
    if isinstance(value, Factor):
        return len(value.values)
    if isinstance(value, (str, bool, int, float)):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _kind_character(value: Any) -> bool:
    if isinstance(value, Factor) or isinstance(value, List) or value is NULL:
        return False
    if isinstance(value, str):
        return True
    if isinstance(value, list) and value and all(isinstance(item, str) or item is None for item in value):
        return True
    return False


def format_glimpse_(value: Any) -> list[Any]:
    if isinstance(value, Factor):
        levels = [item for item in value.values if isinstance(item, str)]
        quote = any("," in item for item in levels)
        if quote:
            return _character(value.values)
        shown = ["NA" if item is None or is_na(item) else str(item) for item in value.values]
        missing = [item is None or is_na(item) for item in value.values]
        return _style_na_if(shown, missing)
    if _kind_character(value):
        items = [value] if isinstance(value, str) else list(value)
        return _character(items)
    if isinstance(value, List):
        return format_glimpse_list(value, inner=False)
    if value is NULL:
        return ["NULL"]
    if isinstance(value, (str, bool, int, float)) or value is None:
        return _atomic([value])
    if isinstance(value, (list, tuple)):
        return _atomic(list(value))
    return [paste_atom(value)]


def format_glimpse_1(value: Any, inner: bool = False) -> str:
    parts = format_glimpse_(value)
    texts = ["NA" if item is None else str(item) for item in parts]
    if inner:
        return ", ".join(texts)
    comma = style_subtle(", ")
    if not isinstance(comma, str):
        comma = ", "
    return comma.join(texts)


def format_glimpse_list(value: List, inner: bool = False) -> list[str]:
    if not inner and len(value.items) == 0:
        return ["list()"]
    out: list[str] = []
    for item in value.items:
        text = format_glimpse_1(item, inner=True)
        listed = isinstance(item, List)
        scalar = _length(item) == 1 and not listed and item is not NULL
        if item is NULL or (not listed and not scalar):
            text = "<" + text + ">"
        if listed:
            text = "[" + text + "]"
        out.append(text)
    return out


def format_glimpse(x: Any, **kwargs: Any) -> Any:
    """One string per element. Lists use ``[]``; other non-scalars use ``<>``."""

    if kwargs:
        raise TypeError("unused arguments")
    if isinstance(x, List):
        rendered = format_glimpse_list(x, inner=False)
    elif isinstance(x, DataFrame):
        rendered = [format_glimpse_1(values) for values in x.columns.values()]
    else:
        rendered = format_glimpse_(x)
    if isinstance(rendered, str):
        return rendered
    return rendered


def _column_map(x: Any) -> DataFrame:
    if isinstance(x, DataFrame):
        return x
    if isinstance(x, dict):
        return DataFrame(x)
    raise TypeError("glimpse() expects a data frame")


def glimpse(x: Any, width: Any = None, **kwargs: Any) -> Any:
    """Print rows, columns, and a one-line preview of each column.

    The default method in R is ``utils::str``. This port prints the data frame
    method, which is the one ``glimpse()`` uses for a tibble or data frame.
    """

    if kwargs:
        raise TypeError("unused arguments")
    if width is not None and isinstance(width, float) and width != width or width == float("inf") or width == float("-inf"):
        raise ValueError("`width` must be finite.")
    if not isinstance(x, (DataFrame, dict)):
        text = str(x)
        cat_line(text)
        return x
    chosen = width_print(width)
    frame = _column_map(x)
    rows_total = frame.nrow
    cat_line("Rows: ", big_mark(rows_total))
    preview = int(chosen / 3)
    head = DataFrame({name: list(values)[:preview] for name, values in frame.columns.items()})
    cat_line("Columns: ", big_mark(head.ncol))
    if head.ncol == 0:
        return x
    types = []
    for values in head.columns.values():
        rendered = new_pillar_type(values).format()
        types.append(rendered if isinstance(rendered, str) else str(rendered))
    names = tick_if_needed(list(head.columns))
    titled = new_pillar_title(names).format()
    if isinstance(titled, str):
        titled = [titled]
    padded = align_names(list(titled))
    var_names = [f"$ {name} {type_} " for name, type_ in zip(padded, types)]
    extents = display_extent(var_names)
    if isinstance(extents, int):
        extents = [extents]
    data_widths = [int(chosen) - int(extent) - 1 for extent in extents]
    formatted = [format_glimpse_1(values) for values in head.columns.values()]
    truncated = [
        str_trunc([item], data_width)[0]
        for item, data_width in zip(formatted, data_widths)
    ]
    for name, data in zip(var_names, truncated):
        cat_line(name + data)
    return x


def align_names(names: list[str]) -> list[str]:
    from pillar.extent import align

    padded = align(names)
    if isinstance(padded, str):
        return [padded]
    return list(padded)
