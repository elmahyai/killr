"""Check that an argument is a data frame (``check_data_frame``)."""

from __future__ import annotations

from typing import Any

from rlang import abort, caller_env
from rlang.check_bool import (
    _caller_arg,
    _format_arg,
    _format_code,
    _number_label,
    _oxford_comma,
)
from rlang.na_or import NA, Character, Complex, Double, Integer, Logical

_MISSING = object()


def _is_data_frame(x: object) -> bool:
    klass = getattr(x, "klass", None)
    if klass is None:
        return False
    if isinstance(klass, str):
        return klass == "data.frame"
    return "data.frame" in klass


def _obj_type_friendly(x: object, *, value: bool = True) -> str:
    if x is _MISSING:
        return "absent"
    if x is None:
        return "`NULL`"
    if _is_data_frame(x):
        return "a data frame"
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
    if isinstance(x, Integer):
        if len(x) == 0:
            return "an empty integer vector"
        if len(x) == 1:
            item = x.values[0]
            if item is NA:
                return "an integer `NA`"
            if isinstance(item, int) and not isinstance(item, bool):
                return _number_label(item) if value else "an integer"
        return "an integer vector"
    if isinstance(x, Double):
        if len(x) == 0:
            return "an empty numeric vector"
        if len(x) == 1:
            item = x.values[0]
            if isinstance(item, float):
                return _number_label(item) if value else "a number"
        return "a numeric vector"
    if isinstance(x, Complex):
        if len(x) == 0:
            return "an empty complex vector"
        return "a complex vector"
    if isinstance(x, Character):
        if len(x) == 0:
            return "an empty character vector"
        if len(x) == 1:
            item = x.values[0]
            if item is NA:
                return "a character `NA`"
            if isinstance(item, str):
                return "a string" if value else "a string"
        return "a character vector"
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


def check_data_frame(
    x: Any = _MISSING,
    *args: Any,
    allow_null: bool = False,
    arg: Any = _MISSING,
    call: Any = _MISSING,
    **kwargs: Any,
) -> None:
    del args, kwargs
    if arg is _MISSING:
        arg = _caller_arg(x)
    if call is _MISSING:
        call = caller_env()
    if x is not _MISSING:
        if _is_data_frame(x):
            return None
        if allow_null and x is None:
            return None
    _stop_input_type(
        x,
        "a data frame",
        allow_na=False,
        allow_null=allow_null,
        arg=str(arg),
        call=call,
    )
