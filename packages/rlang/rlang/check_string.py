"""Check that an argument is a scalar string (``check_string``)."""

from __future__ import annotations

import json
from typing import Any

from rlang import abort, caller_env
from rlang.check_bool import (
    _caller_arg,
    _format_arg,
    _format_code,
    _number_label,
    _oxford_comma,
)
from rlang.na_or import NA, Character

_MISSING = object()


def _str_encode(value: str, width: int = 30) -> str:
    if len(value) > width:
        value = value[: width - 3] + "..."
    return json.dumps(value)


def _obj_type_friendly(x: object, *, value: bool = True) -> str:
    if x is _MISSING:
        return "absent"
    if x is None:
        return "`NULL`"
    if isinstance(x, Character):
        if len(x) == 0:
            return "an empty character vector"
        if len(x) == 1:
            item = x.values[0]
            if item is NA:
                return "a character `NA`"
            if isinstance(item, str):
                if value:
                    what = "the string" if item else "the empty string"
                    return f"{what} {_str_encode(item)}"
                return "a string" if item else '""'
        return "a character vector"
    if isinstance(x, (list, tuple)):
        if len(x) == 1 and not isinstance(x[0], (list, tuple, dict)):
            return _obj_type_friendly(x[0], value=value)
        if len(x) > 1 and all(isinstance(item, str) for item in x):
            return "a character vector"
        if len(x) == 0:
            return "an empty list"
        return "a list"
    if x is NA:
        return "`NA`"
    if isinstance(x, bool):
        if value:
            return "`TRUE`" if x else "`FALSE`"
        return "a logical value"
    if isinstance(x, str):
        if value:
            what = "the string" if x else "the empty string"
            return f"{what} {_str_encode(x)}"
        return "a string" if x else '""'
    if isinstance(x, int) and not isinstance(x, bool):
        return _number_label(x) if value else "an integer"
    if isinstance(x, float):
        return _number_label(x) if value else "a number"
    if isinstance(x, dict):
        return "an environment"
    return f"a {type(x).__name__}"


def _rlang_check_is_string(
    x: object,
    *,
    allow_empty: bool,
    allow_na: bool,
    allow_null: bool,
) -> bool:
    if isinstance(x, Character):
        if len(x) != 1:
            return False
        item = x.values[0]
        if item is NA:
            return allow_na
        if isinstance(item, str):
            return allow_empty or item != ""
        return False

    if isinstance(x, (list, tuple)) and len(x) == 1:
        x = x[0]

    if isinstance(x, str):
        return allow_empty or x != ""

    if allow_null and x is None:
        return True

    if allow_na and x is NA:
        return True

    return False


def _stop_input_type(
    x: object,
    what: str,
    *,
    allow_na: bool,
    allow_null: bool,
    arg: str,
    call: object,
) -> None:
    del call
    parts = [what]
    if allow_na:
        parts.append(_format_code("NA"))
    if allow_null:
        parts.append(_format_code("NULL"))
    message = (
        f"{_format_arg(arg)} must be {_oxford_comma(parts)}, not {_obj_type_friendly(x)}."
    )
    abort(message)


def check_string(
    x: Any = _MISSING,
    *args: Any,
    allow_empty: bool = True,
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
    if x is not _MISSING and _rlang_check_is_string(
        x,
        allow_empty=allow_empty,
        allow_na=allow_na,
        allow_null=allow_null,
    ):
        return None
    _stop_input_type(
        x,
        "a single string",
        allow_na=allow_na,
        allow_null=allow_null,
        arg=str(arg),
        call=call,
    )
