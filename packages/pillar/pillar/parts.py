"""Column title, column type, and the component that holds either one.

A title pads to the widest name. Bold is style_bold, and pillar.bold
defaults to false, so the text has no ANSI codes. A type is type_sum
inside angle brackets, subtle and italic. Its width is at least 5.
A component stores one list element and integer widths.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

from cli.ansi_text import ansi_substr
from cli.symbol import symbol
from cli.unicode_output import is_utf8_output

from pillar._color import underline
from pillar._options import get_option
from pillar._text import is_na
from pillar._vec import NULL
from pillar.extent import align, get_extent, get_max_extent
from pillar.styles import format_type_sum, style_bold
from pillar.summary import type_sum

_MISSING = object()
_MIN_PILLAR_WIDTH = 5
_SUPER = (
    "\u00b9",
    "\u00b2",
    "\u00b3",
    "\u2074",
    "\u2075",
    "\u2076",
    "\u2077",
    "\u2078",
    "\u2079",
    "\u02df",
)
_FOOTNOTE_MARK = "\u02df"
_INT_MAX = 2147483647
_INT_MIN = -2147483647


def _not_true(expression: str) -> None:
    raise ValueError(f"{expression} is not TRUE")


def _show_dot(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    return str(value)


def _reject_dots(args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    """check_dots_empty. Title and type warn in R; an error carries the same text."""

    lines = ["`...` must be empty.", f"{symbol['cross']} Problematic argument:"]
    for index, value in enumerate(args, start=1):
        lines.append(f"{symbol['bullet']} ..{index} = {_show_dot(value)}")
    for name, value in kwargs.items():
        lines.append(f"{symbol['bullet']} {name} = {_show_dot(value)}")
    if args:
        lines.append(f"{symbol['info']} Did you forget to name an argument?")
    raise ValueError("\n".join(lines))


def _is_integerish(value: Any) -> bool:
    """rlang::is_integerish for one number. A bool is not numeric."""

    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return abs(value) <= 2**52
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return True
        if abs(value) > 2**52:
            return False
        return value == math.trunc(value)
    return False


def _as_r_integer(value: Any) -> int | None:
    """as.integer. A non-finite value or a number outside 32-bit range is NA."""

    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, float) and math.isinf(value):
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    number = math.trunc(float(value))
    if number < _INT_MIN or number > _INT_MAX:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    return int(number)


def _one_integer(value: Any, label: str) -> int | None:
    if not _is_integerish(value):
        _not_true(f"is_integerish({label})")
    return _as_r_integer(value)


def _blank_title(item: Any) -> bool:
    return is_na(item) or item == ""


def _title_data(x: Any) -> Any:
    """NULL, or a string, or a list. All-missing and all-blank become NULL."""

    if x is None or x is NULL:
        return None
    scalar = isinstance(x, str) or is_na(x)
    if scalar:
        items = [x]
    elif isinstance(x, list):
        items = list(x)
    else:
        raise TypeError("title must be a string, None, or a list of strings")
    if all(_blank_title(item) for item in items):
        return None
    for item in items:
        if not is_na(item) and not isinstance(item, str):
            raise TypeError("title must be a string or a missing value")
    if scalar:
        return items[0]
    return items


def _str_trunc(x: Any, width: Any, shorten: str) -> Any:
    """Shorten strings wider than width. Inf leaves every string unchanged."""

    if isinstance(width, float) and math.isinf(width):
        return x
    scalar = isinstance(x, str) or is_na(x)
    items = [x] if scalar else list(x)
    if not items:
        return x
    extents = get_extent(items)
    too = [
        index
        for index, (item, extent) in enumerate(zip(items, extents))
        if not is_na(item) and extent > width
    ]
    if too:
        picked = [items[index] for index in too]
        picked_extent = [extents[index] for index in too]
        replaced = _add_ellipsis(picked, picked_extent, width, shorten)
        for index, value in zip(too, replaced):
            items[index] = value
    if scalar:
        return items[0]
    return items


def _add_ellipsis(items: list[Any], extents: list[int], width: Any, shorten: str) -> list[Any]:
    if not items:
        return []
    if shorten not in ("untick", "untick_footnote"):
        raise ValueError(f"unknown shorten {shorten}")
    if len(items) != 1:
        _not_true("length(x) == 1")
    if not extents[0] > width:
        _not_true("str_width > width")
    return [_untick(items[0], width, footnote=shorten == "untick_footnote")]


def _untick(text: str, width: Any, footnote: bool) -> str:
    # Footnotes reserve one column, then the ellipsis takes one grapheme.
    if footnote:
        width = width - 1
    stripped = text.replace("`", "")
    if stripped != text:
        text = stripped
    abbr = ansi_substr(text, 1, width - 1)
    abbr = abbr + symbol["continue"]
    if footnote:
        abbr = abbr + _FOOTNOTE_MARK
    return abbr


def _format_title(x: Any, width: Any, footnote: bool) -> Any:
    shorten = "untick_footnote" if footnote else "untick"
    return align(_str_trunc(x, width, shorten))


def _superdigit(index: Any) -> str:
    if is_utf8_output():
        slot = min(float(index), 10)
        whole = math.trunc(slot)
        if slot != whole or whole < 1:
            raise ValueError("attempt to select more than one element in integerOneIndex")
        return _SUPER[whole - 1]
    if index >= 10:
        return "*"
    return str(int(index))


def _apply_footnote(text: Any, index: Any) -> Any:
    digit = _superdigit(index)

    def one(item: Any) -> Any:
        if isinstance(item, str) and item.endswith(_FOOTNOTE_MARK):
            return item[:-1] + digit
        return item

    if isinstance(text, str) or is_na(text):
        return one(text)
    return [one(item) for item in text]


def _numeric_scalar(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _min_title_width(width: int) -> Any:
    title_chars = get_option("pillar.min_title_chars")
    if not _numeric_scalar(title_chars):
        raise ValueError("Option pillar.min_title_chars must be a nonnegative number")
    if isinstance(title_chars, float) and math.isnan(title_chars):
        raise ValueError("missing value where TRUE/FALSE needed")
    if title_chars < 0:
        raise ValueError("Option pillar.min_title_chars must be a nonnegative number")
    if isinstance(title_chars, float) and math.isinf(title_chars):
        return width
    if width <= title_chars:
        return width
    return title_chars + 2


class PillarTitle:
    """A column title and the widths format() will use."""

    def __init__(self, x: Any, width: int, min_width: int):
        self.x = x
        self.width = width
        self.min_width = min_width

    def format(self, width: Any = None, footnote_idx: int = 0, **_ignored: Any) -> Any:
        """Render the titles. An omitted width uses the stored width."""

        if self.x is None:
            return []
        use = self.width if width is None else width
        footnote = footnote_idx > 0
        title = _format_title(self.x, use, footnote)
        if footnote:
            title = _apply_footnote(title, footnote_idx)
        return style_bold(title)

    def __repr__(self) -> str:
        return f"pillar_title({self.x!r}, width={self.width}, min_width={self.min_width})"


def new_pillar_title(x: Any, *args: Any, **kwargs: Any) -> PillarTitle:
    """Prepare column titles. format() renders them, padded on the right.

    NULL, and a vector that is entirely missing or "", has width 0.
    Any other title's width is the widest formatted name. The minimum
    width equals that width when it is at most pillar.min_title_chars,
    or when that option is infinite. Otherwise the minimum is the option
    plus 2, truncated toward zero.
    """

    if args or kwargs:
        _reject_dots(args, kwargs)
    data = _title_data(x)
    if data is None:
        width = 0
    else:
        width = get_max_extent(_format_title(data, float("inf"), True))
        if isinstance(width, float) and math.isnan(width):
            _not_true("!is.na(width)")
        width = int(width)
    minimum = _as_r_integer(min(width, _min_title_width(width)))
    return PillarTitle(data, width, 0 if minimum is None else minimum)


class PillarType:
    """A column type label and its widths."""

    def __init__(self, x: Any, width: int, min_width: int):
        self.x = x
        self.width = width
        self.min_width = min_width

    def format(self, width: Any = None, is_focus: bool = False, **_ignored: Any) -> Any:
        """Render the type. is_focus underlines the subtle italic label."""

        out = format_type_sum(self.x, width)
        if is_focus:
            return underline(out)
        return out

    def __repr__(self) -> str:
        return f"pillar_type({self.x!r}, width={self.width}, min_width={self.min_width})"


def _pillar_type_name(x: Any) -> Any:
    """type_sum, or \"?\" when that summary has length zero."""

    name = type_sum(x)
    if isinstance(name, list):
        if not name:
            return "?"
        return name[0]
    return name


def new_pillar_type(x: Any, *args: Any, **kwargs: Any) -> PillarType:
    """Prepare a column type. format() renders type_sum inside brackets.

    The width is the display width of that styled label, and at least 5.
    The minimum width is 5.
    """

    if args or kwargs:
        _reject_dots(args, kwargs)
    name = _pillar_type_name(x)
    styled = format_type_sum(name, None)
    extent = get_extent(styled)
    if isinstance(extent, list):
        extent = max(extent) if extent else 0
    width = max(int(extent), _MIN_PILLAR_WIDTH)
    return PillarType(name, width, _MIN_PILLAR_WIDTH)


class PillarComponent:
    """One piece of a pillar: a length-one list plus two integer widths."""

    def __init__(self, x: list[Any], width: int | None, min_width: int | None):
        self.x = x
        self.width = width
        self.min_width = min_width

    def __repr__(self) -> str:
        return f"pillar_component({self.x!r}, width={self.width}, min_width={self.min_width})"


def new_pillar_component(
    x: Any,
    *args: Any,
    width: Any = _MISSING,
    min_width: Any = None,
    **kwargs: Any,
) -> PillarComponent:
    """Store one list element with a width and a minimum width.

    x is a bare list of length one. width is one integer-valued number.
    min_width defaults to width. Both are stored as integers. NA is None.
    """

    if args or kwargs:
        _reject_dots(args, kwargs)
    if width is _MISSING:
        raise TypeError('argument "width" is missing, with no default')
    if type(x) is not list:
        _not_true("rlang::is_bare_list(x)")
    if len(x) != 1:
        _not_true("length(x) == 1")
    width_int = _one_integer(width, "width")
    if min_width is None:
        min_int = width_int
    else:
        min_int = _one_integer(min_width, "min_width")
    return PillarComponent(list(x), width_int, min_int)


def pillar_component(x: Any) -> PillarComponent:
    """Wrap x in a component, copying its width and minimum width.

    A missing minimum width is the width, the way get_min_width falls back.
    """

    if "min_width" in vars(x):
        min_width = x.min_width
    else:
        min_width = x.width
    return new_pillar_component([x], width=x.width, min_width=min_width)
