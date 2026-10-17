"""Check that an argument is a scalar logical (``check_bool``)."""

from __future__ import annotations

import sys
from typing import Any

from rlang import abort, caller_env
from rlang.na_or import NA, Logical

_MISSING = object()


def _format_arg(arg: str) -> str:
    return f"`{arg}`"


def _format_code(code: str) -> str:
    return f"`{code}`"


def _oxford_comma(parts: list[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} or {parts[1]}"
    return f"{', '.join(parts[:-1])}, or {parts[-1]}"


def _number_label(x: int | float) -> str:
    rounded = round(float(x), 2)
    if rounded == int(rounded):
        text = str(int(rounded))
    else:
        text = str(rounded)
    return f"the number {text}"


def _obj_type_friendly(x: object, *, value: bool = True) -> str:
    if x is _MISSING:
        return "absent"
    if x is None:
        return "`NULL`"
    if isinstance(x, Logical):
        if len(x) == 0:
            return "an empty logical vector"
        if len(x) == 1:
            item = x.values[0]
            if item is NA:
                return "`NA`"
            if isinstance(item, bool):
                if value:
                    return "`TRUE`" if item else "`FALSE`"
                return "a logical value"
        return "a logical vector"
    if isinstance(x, bool):
        if value:
            return "`TRUE`" if x else "`FALSE`"
        return "a logical value"
    if x is NA:
        return "`NA`"
    if isinstance(x, int) and not isinstance(x, bool):
        return _number_label(x) if value else "an integer"
    if isinstance(x, float):
        return _number_label(x) if value else "a number"
    if isinstance(x, str):
        return "a string" if value else "a string"
    if isinstance(x, list):
        return "a list"
    if isinstance(x, dict):
        return "an environment"
    return f"a {type(x).__name__}"


def _caller_arg(arg: object) -> str:
    frame = sys._getframe(2)
    for name, value in frame.f_locals.items():
        if value is arg:
            return name
    return ""


def _standalone_is_bool(x: object, allow_na: bool, allow_null: bool) -> bool:
    if x is None:
        return allow_null
    if isinstance(x, Logical):
        if len(x) != 1:
            return False
        value = x.values[0]
        if value is NA:
            return allow_na
        return isinstance(value, bool)
    if x is NA:
        return allow_na
    if isinstance(x, bool):
        return True
    return False


def _stop_input_type(
    x: object,
    what: list[str],
    *,
    allow_na: bool,
    allow_null: bool,
    arg: str,
    call: object,
) -> None:
    del call
    parts = list(what)
    if allow_na:
        parts.append(_format_code("NA"))
    if allow_null:
        parts.append(_format_code("NULL"))
    message = (
        f"{_format_arg(arg)} must be {_oxford_comma(parts)}, not {_obj_type_friendly(x)}."
    )
    abort(message)


def check_bool(
    x: Any = _MISSING,
    *args: Any,
    allow_na: bool = False,
    allow_null: bool = False,
    arg: Any = _MISSING,
    call: Any = _MISSING,
    **kwargs: Any,
) -> None:
    del args, kwargs
    if arg is _MISSING:
        arg = _caller_arg(x) if x is not _MISSING else ""
    if call is _MISSING:
        call = caller_env()
    if x is not _MISSING and _standalone_is_bool(x, allow_na, allow_null):
        return None
    _stop_input_type(
        x,
        [_format_code("TRUE"), _format_code("FALSE")],
        allow_na=allow_na,
        allow_null=allow_null,
        arg=str(arg),
        call=call,
    )
