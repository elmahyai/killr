"""Scalar assertions from assertions-scalar.R."""

from __future__ import annotations

import math
from typing import Any

from assertthat.expr import register
from assertthat.failure import on_failure
from assertthat.objects import (
    elements,
    is_character,
    is_integer_mode,
    is_logical,
    is_missing,
    is_numeric,
    length,
    r_all,
    r_and,
)


def is_integerish(x: Any) -> bool:
    """Unexported helper behind is.count. Integer storage is integerish, NA included."""
    if is_integer_mode(x):
        return True
    if not is_numeric(x):
        return False
    values = elements(x)
    compared: list[Any] = []
    missing: list[bool] = []
    for value in values:
        if is_missing(value):
            compared.append(None)
            missing.append(True)
            continue
        missing.append(False)
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            compared.append(True if math.isinf(value) else None)
            continue
        number = float(value)
        compared.append(number == math.trunc(number))
    from assertthat.objects import NA

    flags = [NA if item is None else item for item in compared]
    all_equal = r_all(flags)
    if len(values) != 1:
        return False
    not_missing = False if missing[0] else True
    return r_and(all_equal, not_missing) is True


def is_scalar(x: Any) -> bool:
    return length(x) == 1


def _scalar_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    from assertthat.see import _deparse_one

    return f"{_deparse_one(call['x'])} is not a scalar."


def is_string(x: Any) -> bool:
    return is_character(x) and length(x) == 1


def _string_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    from assertthat.see import _deparse_one

    return f"{_deparse_one(call['x'])} is not a string (a length one character vector)."


def is_number(x: Any) -> bool:
    return is_numeric(x) and length(x) == 1


def _number_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    from assertthat.see import _deparse_one

    return f"{_deparse_one(call['x'])} is not a number (a length one numeric vector)."


def is_flag(x: Any) -> bool:
    return is_logical(x) and length(x) == 1


def _flag_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    from assertthat.see import _deparse_one

    return f"{_deparse_one(call['x'])} is not a flag (a length one logical vector)."


def is_count(x: Any) -> bool:
    if length(x) != 1:
        return False
    if not is_integerish(x):
        return False
    if is_missing(x):
        return False
    return float(x) > 0


def _count_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    from assertthat.see import _deparse_one

    return f"{_deparse_one(call['x'])} is not a count (a single positive integer)"


def install_scalar() -> None:
    register("is.scalar", is_scalar, ["x"])
    register("is.string", is_string, ["x"])
    register("is.number", is_number, ["x"])
    register("is.flag", is_flag, ["x"])
    register("is.count", is_count, ["x"])
    on_failure(is_scalar, _scalar_fail)
    on_failure(is_string, _string_fail)
    on_failure(is_number, _number_fail)
    on_failure(is_flag, _flag_fail)
    on_failure(is_count, _count_fail)


install_scalar()
