"""``str_glue`` and ``str_glue_data`` call the translated glue functions."""

from __future__ import annotations

import inspect
from typing import Any

from glue import glue, glue_data
from glue.interpolate import Glue
from stringi._na import NA


def _caller_names() -> dict[str, Any]:
    """Names visible to the function that called ``str_glue`` or ``str_glue_data``."""

    frame = inspect.currentframe()
    caller = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
    if caller is None:
        return {}
    names = {key: value for key, value in caller.f_globals.items() if not key.startswith("__")}
    names.update({key: value for key, value in caller.f_locals.items() if not key.startswith("__")})
    return names


def _as_character(value: Any) -> list:
    """A glue result as a character vector. A missing piece stays ``NA``."""

    if isinstance(value, Glue):
        return [NA if item is NA else item for item in value.values]
    if value is NA:
        return [NA]
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [NA if item is NA else item for item in value]
    return [value]


def str_glue(*parts: Any, sep: str = "", envir: dict[str, Any] | None = None, trim: bool = True, **named: Any) -> list:
    """Interpolate ``parts`` with ``glue``.

    Unnamed strings are the template. Named arguments are values the braces
    can see. ``sep`` joins the template strings first. ``trim`` drops the
    common indent. When ``envir`` is omitted, the caller's names are visible.
    """

    if envir is None:
        envir = _caller_names()
    return _as_character(glue(*parts, sep=sep, envir=envir, trim=trim, **named))


def str_glue_data(
    x: Any,
    *parts: Any,
    sep: str = "",
    envir: dict[str, Any] | None = None,
    na: Any = "NA",
    **named: Any,
) -> list:
    """Interpolate ``parts`` with ``glue_data``.

    Names come from ``x``, then ``envir``, then the named arguments. ``na``
    replaces a missing piece. The default is the letters ``NA``.
    """

    if envir is None:
        envir = _caller_names()
    return _as_character(glue_data(x, *parts, sep=sep, envir=envir, na=na, **named))
