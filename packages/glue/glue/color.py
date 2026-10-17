"""ANSI color styles matching the crayon codes glue_col calls."""

from __future__ import annotations

import re
from typing import Any

from glue._eval import identity_transformer
from glue._scan import GlueError
from glue._text import NA, Glue
from glue.interpolate import _caller_names, glue, glue_data

_STYLE_CODES = {
    "reset": (0, 0),
    "bold": (1, 22),
    "blurred": (2, 22),
    "italic": (3, 23),
    "underline": (4, 24),
    "inverse": (7, 27),
    "hidden": (8, 28),
    "strikethrough": (9, 29),
    "black": (30, 39),
    "red": (31, 39),
    "green": (32, 39),
    "yellow": (33, 39),
    "blue": (34, 39),
    "magenta": (35, 39),
    "cyan": (36, 39),
    "white": (37, 39),
    "silver": (90, 39),
    "bgBlack": (40, 49),
    "bgRed": (41, 49),
    "bgGreen": (42, 49),
    "bgYellow": (43, 49),
    "bgBlue": (44, 49),
    "bgMagenta": (45, 49),
    "bgCyan": (46, 49),
    "bgWhite": (47, 49),
}

_COLOR_CALL = re.compile(r"(?s)^([A-Za-z0-9_]+)\s+(.+)\Z")


def _tag(code: int) -> str:
    return f"\033[{code}m"


def paint(text: Any, open_code: int, close_code: int) -> Any:
    """Apply one crayon style. A close code inside the text becomes the open code."""

    open_s = _tag(open_code)
    close_s = _tag(close_code)

    def one(item: Any) -> Any:
        if item is NA:
            return NA
        body = item.values[0] if isinstance(item, Glue) and len(item.values) == 1 else item
        if isinstance(body, Glue):
            return Glue(tuple(one(value) for value in body.values))
        if body is NA:
            return NA
        return open_s + str(body).replace(close_s, open_s) + close_s

    if isinstance(text, Glue):
        painted = tuple(one(value) for value in text.values)
        if len(painted) == 1:
            return painted[0]
        return Glue(painted)
    if isinstance(text, (list, tuple)):
        return tuple(one(value) for value in text)
    return one(text)


def _make_style(open_code: int, close_code: int):
    def apply(text: Any) -> Any:
        return paint(text, open_code, close_code)

    return apply


STYLES = {name: _make_style(*codes) for name, codes in _STYLE_CODES.items()}


def _lookup(name: str, envir: dict[str, Any]) -> Any:
    value = envir.get(name)
    if callable(value) and not isinstance(value, type):
        return value
    if name in STYLES:
        return STYLES[name]
    raise GlueError(f"object '{name}' of mode 'function' was not found")


def color_transformer(code: str, envir: dict[str, Any]) -> Any:
    try:
        return identity_transformer(code, envir)
    except GlueError:
        match = _COLOR_CALL.match(code)
        if match is None:
            raise
        nested = glue(
            match.group(2),
            envir=envir,
            transformer=color_transformer,
            trim=True,
        )
        return _lookup(match.group(1), envir)(nested)


def glue_col(
    *parts: Any,
    envir: dict[str, Any] | None = None,
    na: Any = "NA",
    literal: bool = False,
    **named: Any,
) -> Glue:
    """glue with crayon style names. ``{blue foo}`` colors foo."""

    if envir is None:
        envir = _caller_names()
    return glue(
        *parts,
        envir=envir,
        na=na,
        literal=literal,
        transformer=color_transformer,
        **named,
    )


def glue_data_col(
    x: Any,
    *parts: Any,
    envir: dict[str, Any] | None = None,
    na: Any = "NA",
    literal: bool = False,
    **named: Any,
) -> Glue:
    """glue_data with the same color syntax as glue_col."""

    if envir is None:
        envir = _caller_names()
    return glue_data(
        x,
        *parts,
        envir=envir,
        na=na,
        literal=literal,
        transformer=color_transformer,
        **named,
    )
