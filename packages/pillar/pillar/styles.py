"""Subtle, bold, and negative styles, and the type label in a column header.

Empty strings stay empty in the styles that use keep_empty. A missing value
that is painted is the letters NA, because crayon pastes with paste0.
as.character of a missing number stays missing. That is the path ifelse takes
when a negative flag is false and some other flag has already made the result
character.
"""

from __future__ import annotations

import math
from typing import Any, Callable

from glue._text import r_character_double

from pillar._color import bold, grey_0_6, italic, red
from pillar._options import get_option
from pillar._text import is_na
from pillar._width import display_extent


class AsIs(str):
    """A string marked the way R's I() marks it.

    format_type_sum prints an AsIs string without angle brackets.
    """

    def __new__(cls, text: str) -> AsIs:
        if not isinstance(text, str):
            raise TypeError("AsIs text must be a string")
        return str.__new__(cls, text)


def _option_true(name: str) -> bool:
    """isTRUE of a pillar option. Only a real True counts."""

    return get_option(name) is True


def _elements(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return [value]


def _count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 1


def _as_character(item: Any) -> Any:
    """R as.character of one atom. A missing value stays missing."""

    if is_na(item):
        return None
    if isinstance(item, str):
        return item
    if isinstance(item, bool):
        return "TRUE" if item else "FALSE"
    if isinstance(item, int):
        return str(item)
    if isinstance(item, float):
        return r_character_double(item)
    return str(item)


def _selected(item: Any) -> bool:
    """keep_empty updates a missing value and anything other than ""."""

    if is_na(item):
        return True
    if isinstance(item, str):
        return item != ""
    return True


def _keep_empty(x: Any, fun: Callable[[list[Any]], list[Any]]) -> Any:
    """Start from blanks and replace only the values fun is allowed to see."""

    scalar = not isinstance(x, list)
    items = [x] if scalar else list(x)
    result: list[Any] = [""] * len(items)
    chosen = [item for item in items if _selected(item)]
    if chosen:
        styled = fun(chosen)
        index = 0
        for position, item in enumerate(items):
            if _selected(item):
                result[position] = styled[index]
                index += 1
    if scalar:
        return result[0]
    return result


def _paint_or_character(items: list[Any], paint: Callable[[list[Any]], Any], enabled: bool) -> list[Any]:
    if not items:
        return []
    if enabled:
        painted = paint(items)
        if isinstance(painted, list):
            return painted
        return [painted]
    return [_as_character(item) for item in items]


def _subtle_apply(items: list[Any]) -> list[Any]:
    return _paint_or_character(items, grey_0_6, _option_true("pillar.subtle"))


def _bold_apply(items: list[Any]) -> list[Any]:
    return _paint_or_character(items, bold, _option_true("pillar.bold"))


def _neg_apply(items: list[Any]) -> list[Any]:
    return _paint_or_character(items, red, _option_true("pillar.neg"))


def style_subtle(x: Any) -> Any:
    """Grey text when pillar.subtle is true. Empty strings stay empty."""

    return _keep_empty(x, _subtle_apply)


def style_bold(x: Any) -> Any:
    """Bold text when pillar.bold is true. Empty strings stay empty."""

    return _keep_empty(x, _bold_apply)


def style_neg(x: Any) -> Any:
    """Red text when pillar.neg is true. Empty strings stay empty."""

    return _keep_empty(x, _neg_apply)


def style_na(x: Any) -> Any:
    """Paint every element red, including an empty string."""

    if isinstance(x, list):
        return red(x)
    if isinstance(x, str) or is_na(x):
        return red(x)
    return red([x])[0]


def _as_logical(item: Any) -> bool | None:
    """storage.mode<- "logical". Zero is false, NaN and missing are NA."""

    if is_na(item):
        return None
    if isinstance(item, bool):
        return item
    if isinstance(item, int):
        return item != 0
    if isinstance(item, float):
        if math.isnan(item):
            return None
        return item != 0.0
    raise TypeError("negative must be logical")


def _recycle(items: list[Any], length: int) -> list[Any]:
    """rep(items, length.out = length). An empty source becomes missing."""

    if length == 0:
        return []
    if not items:
        return [None] * length
    if len(items) == length:
        return list(items)
    return [items[index % len(items)] for index in range(length)]


def _match_shape(value: Any, scalar: bool) -> Any:
    if scalar:
        if isinstance(value, list):
            return value[0] if value else None
        return value
    if isinstance(value, list):
        return value
    return [value]


def _negative_or_plain(x: Any, negative: Any) -> Any:
    """ifelse(negative, style_neg(x), x). The result has the length of negative."""

    scalar = not isinstance(negative, list)
    flags = [_as_logical(item) for item in _elements(negative)]
    length = len(flags)
    if length == 1 and flags[0] is None:
        return None if scalar else [None]

    any_true = any(flag is True for flag in flags)
    any_false = any(flag is False for flag in flags)
    yes = style_neg(x) if any_true else None
    no = x if any_false else None

    if length == 1 and flags[0] is True and _count(yes) == 1:
        return _match_shape(yes, scalar)
    if length == 1 and flags[0] is False and _count(no) == 1:
        return _match_shape(no, scalar)

    yes_items = _recycle(_elements(yes), length) if any_true else []
    no_items = _recycle(_elements(no), length) if any_false else []
    out: list[Any] = []
    for index, flag in enumerate(flags):
        if flag is True:
            out.append(yes_items[index])
        elif flag is False:
            item = no_items[index]
            out.append(_as_character(item) if any_true else item)
        else:
            out.append(None)
    return out[0] if scalar else out


def style_subtle_num(x: Any, negative: Any) -> Any:
    """Subtle digits, or red negatives, following pillar.subtle_num.

    The result has the length of negative, the way ifelse does. A true flag
    makes the whole result character. A false-only call leaves numbers as
    numbers, because style_neg is not run.
    """

    if _option_true("pillar.subtle_num"):
        return style_subtle(x)
    return _negative_or_plain(x, negative)


def style_num(x: Any, negative: Any, significant: Any = None) -> Any:
    """Significant digits stay plain or red. The rest go through style_subtle_num.

    significant defaults to TRUE for every element of x. The result has the
    length of significant, the way the outer ifelse does.
    """

    if significant is None:
        significant = True if not isinstance(x, list) else [True] * len(x)
    scalar = not isinstance(significant, list)
    flags = [_as_logical(item) for item in _elements(significant)]
    if len(flags) == 1 and flags[0] is None:
        return None if scalar else [None]
    yes = _negative_or_plain(x, negative) if any(flag is True for flag in flags) else None
    no = style_subtle_num(x, negative) if any(flag is False for flag in flags) else None
    if len(flags) == 1 and flags[0] is True:
        return _match_shape(yes, scalar)
    if len(flags) == 1 and flags[0] is False:
        return _match_shape(no, scalar)
    yes_items = _recycle(_elements(yes), len(flags)) if yes is not None else []
    no_items = _recycle(_elements(no), len(flags)) if no is not None else []
    out: list[Any] = []
    for index, flag in enumerate(flags):
        if flag is True:
            out.append(yes_items[index])
        elif flag is False:
            out.append(no_items[index])
        else:
            out.append(None)
    return out[0] if scalar else out


def _style_type(x: Any) -> Any:
    """Subtle, then italic wrapped around that whole string."""

    return italic(style_subtle(x))


def _width_number(width: Any) -> int | float:
    if isinstance(width, bool) or not isinstance(width, (int, float)):
        raise TypeError("non-numeric argument to binary operator")
    if isinstance(width, float) and math.isnan(width):
        raise ValueError("missing value where TRUE/FALSE needed")
    return width


def _r_less(left: Any, right: Any) -> bool:
    if left is None or right is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(left, float) and math.isnan(left):
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(right, float) and math.isnan(right):
        raise ValueError("missing value where TRUE/FALSE needed")
    return left < right


def _substr_r(text: str | None, stop: Any) -> str | None:
    """substr(text, 1, stop). The end is truncated toward zero."""

    if text is None:
        return None
    if isinstance(stop, float) and math.isnan(stop):
        return None
    count = int(math.trunc(float(stop)))
    if count <= 0:
        return ""
    return text[:count]


def _extent_one(item: Any) -> int:
    if is_na(item):
        return display_extent(None)
    if isinstance(item, str):
        return display_extent(item)
    text = _as_character(item)
    if text is None:
        return 2
    return display_extent(text)


def _bracket(item: Any) -> str:
    """paste0("<", item, ">"). A missing item is the letters NA."""

    if is_na(item):
        body = "NA"
    elif isinstance(item, str):
        body = item
    else:
        text = _as_character(item)
        body = "NA" if text is None else text
    return "<" + body + ">"


def _condition_length(count: int) -> None:
    if count == 0:
        raise ValueError("missing value where TRUE/FALSE needed")
    if count > 1:
        raise ValueError(f"'length = {count}' in coercion to 'logical(1)'")


def _format_default(x: Any, width: Any) -> Any:
    scalar = not isinstance(x, list)
    items = [x] if scalar else list(x)
    if width is not None:
        number = _width_number(width)
        _condition_length(len(items))
        if _r_less(number - 2, _extent_one(items[0])):
            items[0] = _substr_r(
                items[0] if isinstance(items[0], str) or is_na(items[0]) else _as_character(items[0]),
                max(number - 2, 0),
            )
    # paste0 drops a zero-length argument, so character(0) becomes "<>".
    brackets = ["<>"] if not items else [_bracket(item) for item in items]
    if scalar or not items:
        return _style_type(brackets[0])
    return _style_type(brackets)


def _format_asis(x: AsIs, width: Any) -> Any:
    text: str | None = str(x)
    if width is not None:
        number = _width_number(width)
        if _r_less(number, display_extent(text)):
            text = _substr_r(text, number)
    return _style_type("" if text is None else text)


def format_type_sum(x: Any, width: Any = None) -> Any:
    """Angle brackets, then subtle italic. AsIs text has no brackets.

    width is the display width of the type text before the brackets are
    added. A short budget keeps max(width - 2, 0) code points of that text.
    An AsIs string is cut to width code points, with no extra two for brackets.
    """

    if isinstance(x, AsIs):
        return _format_asis(x, width)
    return _format_default(x, width)
