"""Base predicates and operators that see_if evaluates."""

from __future__ import annotations

import math
import os
from typing import Any

from assertthat.expr import register
from assertthat.objects import (
    NA,
    Vector,
    elements,
    is_character,
    is_integer_mode,
    is_logical,
    is_missing,
    is_numeric,
    length,
    r_all,
)


def _length(x: Any = None) -> int:
    return length(x)


def _c(*args: Any) -> Vector:
    flat: list[Any] = []
    for arg in args:
        if isinstance(arg, Vector):
            flat.extend(arg.data)
        else:
            flat.append(arg)
    if any(isinstance(item, str) for item in flat):
        mode = "character"
    elif flat and all(is_logical(item) for item in flat):
        mode = "logical"
    elif flat and all(is_integer_mode(item) for item in flat):
        mode = "integer"
    else:
        mode = "double"
    return Vector(flat, mode)


def _flatten(args: tuple[Any, ...]) -> list[Any]:
    values: list[Any] = []
    for arg in args:
        values.extend(elements(arg))
    return values


def _any(*args: Any) -> Any:
    values = _flatten(args)
    if any(item is True for item in values):
        return True
    if any(is_missing(item) for item in values):
        return NA
    return False


def _all(*args: Any) -> Any:
    values = _flatten(args)
    flags = []
    for item in values:
        if is_missing(item):
            flags.append(NA)
        else:
            flags.append(item is True)
    return r_all(flags)


def _is_character(x: Any = None) -> bool:
    return is_character(x)


def _is_numeric(x: Any = None) -> bool:
    return is_numeric(x)


def _is_logical(x: Any = None) -> bool:
    return is_logical(x)


def _is_integer(x: Any = None) -> bool:
    return is_integer_mode(x)


def _is_double(x: Any = None) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, float):
        return True
    if isinstance(x, type(NA)) and x.mode == "double":
        return True
    return isinstance(x, Vector) and x.mode == "double"


def _is_null(x: Any = None) -> bool:
    return x is None


def _is_function(x: Any = None) -> bool:
    return callable(x)


def _file_exists(path: Any = None) -> bool:
    if not isinstance(path, str):
        return False
    return os.path.exists(path)


def _identical(x: Any = None, y: Any = None) -> bool:
    if is_missing(x) or is_missing(y):
        return type(x) is type(y) and getattr(x, "mode", None) == getattr(y, "mode", None) and is_missing(x) and is_missing(y)
    if isinstance(x, float) and isinstance(y, float):
        if math.isnan(x) and math.isnan(y):
            return True
    return x == y and type(x) is type(y)


def _is_true(x: Any = None) -> bool:
    return x is True


def _sqrt(x: Any = None) -> float:
    return math.sqrt(x)


def _sum(x: Any = None) -> float:
    return float(sum(elements(x)))


def _eq(left: Any, right: Any) -> Any:
    if isinstance(left, str) or isinstance(right, str):
        return _as_char(left) == _as_char(right)
    if is_missing(left) or is_missing(right):
        return NA
    return left == right


def _as_char(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if is_missing(value):
        return "NA"
    return str(value)


def _cmp(left: Any, right: Any, op: str) -> Any:
    if is_missing(left) or is_missing(right):
        return NA
    if op == "<":
        return left < right
    if op == ">":
        return left > right
    if op == "<=":
        return left <= right
    if op == ">=":
        return left >= right
    return left != right


def _not(x: Any) -> Any:
    if is_missing(x):
        return NA
    if isinstance(x, Vector):
        return Vector([_not(item) for item in x.data], "logical")
    return not x


def mean(x: Any, *args: Any) -> Any:
    """Stand-in for base::mean. Assertions only read its formals."""
    raise NotImplementedError("mean")


def rnorm(n: Any, mean: float = 0.0, sd: float = 1.0) -> Any:
    """Stand-in for base::rnorm. Assertions only read its formals."""
    raise NotImplementedError("rnorm")


def install_base() -> None:
    register("length", _length, ["x"], primitive=True)
    register("c", _c, ["..."], primitive=True)
    register("any", _any, ["..."], primitive=True)
    register("all", _all, ["..."], primitive=True)
    register("is.character", _is_character, ["x"], primitive=True)
    register("is.numeric", _is_numeric, ["x"], primitive=True)
    register("is.logical", _is_logical, ["x"], primitive=True)
    register("is.integer", _is_integer, ["x"], primitive=True)
    register("is.double", _is_double, ["x"], primitive=True)
    register("is.null", _is_null, ["x"], primitive=True)
    register("is.function", _is_function, ["x"], primitive=True)
    register("file.exists", _file_exists, ["..."], primitive=True)
    register("identical", _identical, ["x", "y"], primitive=True)
    register("isTRUE", _is_true, ["x"], primitive=False)
    register("sqrt", _sqrt, ["x"], primitive=True)
    register("sum", _sum, ["..."], primitive=True)
    register("==", _eq, ["e1", "e2"], primitive=True)
    register("!=", lambda left, right: _cmp(left, right, "!="), ["e1", "e2"], primitive=True)
    register("<", lambda left, right: _cmp(left, right, "<"), ["e1", "e2"], primitive=True)
    register(">", lambda left, right: _cmp(left, right, ">"), ["e1", "e2"], primitive=True)
    register("<=", lambda left, right: _cmp(left, right, "<="), ["e1", "e2"], primitive=True)
    register(">=", lambda left, right: _cmp(left, right, ">="), ["e1", "e2"], primitive=True)
    register("!", _not, ["x"], primitive=True)
    register("mean", mean, ["x", "..."])
    register("rnorm", rnorm, ["n", "mean", "sd"])


install_base()
