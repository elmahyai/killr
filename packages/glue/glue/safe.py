"""Name lookup without evaluating the brace."""

from __future__ import annotations

import inspect
from typing import Any

from glue._eval import get_transformer
from glue.interpolate import glue, glue_data


def _caller_names() -> dict[str, Any]:
    frame = inspect.currentframe()
    caller = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
    if caller is None:
        return {}
    names = {key: value for key, value in caller.f_globals.items() if not key.startswith("__")}
    names.update(
        {key: value for key, value in caller.f_locals.items() if not key.startswith("__")}
    )
    return names


def glue_safe(*parts: Any, envir: dict[str, Any] | None = None, **named: Any):
    """Like glue, but a brace is a name lookup. ``{age + 1}`` is not computed."""

    if envir is None:
        envir = _caller_names()
    return glue(*parts, envir=envir, transformer=get_transformer, **named)


def glue_data_safe(x: Any, *parts: Any, envir: dict[str, Any] | None = None, **named: Any):
    """Like glue_data, with the same name-only lookup as glue_safe."""

    if envir is None:
        envir = _caller_names()
    return glue_data(x, *parts, envir=envir, transformer=get_transformer, **named)
