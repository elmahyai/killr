"""Collapse a vector the way cli::ansi_collapse does when width is infinite."""

from __future__ import annotations

import math

from cli.symbol import symbol
from glue._text import NA, r_character


def _match_arg(value: str, choices: tuple[str, ...]) -> str:
    if value in choices:
        return value
    hits = [choice for choice in choices if choice.startswith(value)]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"style must be one of {', '.join(choices)}")


def _characters(x) -> list:
    if isinstance(x, str):
        return [x]
    if x is None:
        return []
    return list(x)


def _as_character_item(value):
    if value is None or value is NA:
        return None
    if isinstance(value, str):
        return value
    text = r_character(value)
    if text is NA:
        return None
    return text


def collapse_head_notrim(x: list[str], trunc: float, sep: str, sep2: str, last: str, ellipsis: str) -> str:
    length = len(x)
    if length == 1:
        return x[0]
    if length == 2:
        return sep2.join(x)
    if length <= trunc:
        return sep.join(x[:-1]) + last + x[-1]
    return sep.join(x[: int(trunc)]) + sep + ellipsis


def ansi_collapse(
    x,
    sep: str = ", ",
    sep2: str | None = None,
    last: str = ", and ",
    trunc: float = math.inf,
    width: float = math.inf,
    ellipsis: str | None = None,
    style: str = "both-ends",
) -> str | None:
    """Collapse a vector. A missing element makes the whole result missing."""

    if sep2 is None:
        sep2 = last[1:] if last.startswith(",") else last
    chosen = _match_arg(style, ("both-ends", "head"))
    if ellipsis is None:
        ellipsis = symbol["ellipsis"]
    if chosen == "both-ends":
        return _both_ends(x, sep, sep2, last, trunc, width, ellipsis)
    return _head(x, sep, sep2, last, trunc, width, ellipsis)


def _head(x, sep, sep2, last, trunc, width, ellipsis) -> str | None:
    trunc = max(trunc, 1)
    values = [_as_character_item(item) for item in _characters(x)]
    if not values:
        return ""
    if any(item is None for item in values):
        return None
    if width == math.inf:
        return collapse_head_notrim(values, trunc, sep, sep2, last, ellipsis)
    raise NotImplementedError(
        "ansi_collapse width trimming needs display width, which is not translated yet"
    )


def _both_ends(x, sep, sep2, last, trunc, width, ellipsis) -> str | None:
    if width != math.inf:
        width = math.inf
    values = _characters(x)
    trunc = max(trunc, 5)
    trunc = min(trunc, len(values))
    if len(values) <= 5 or len(values) <= trunc:
        return _head(values, sep, sep2, last, trunc, width, ellipsis)
    kept = list(values[: int(trunc) - 2]) + [values[-2], values[-1]]
    shown = [_as_character_item(item) for item in kept]
    if any(item is None for item in shown):
        return None
    pieces = shown[: int(trunc) - 2] + [ellipsis, shown[-2] + last + shown[-1]]
    return sep.join(pieces)
