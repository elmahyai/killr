"""General assertions from assertions.r."""

from __future__ import annotations

import math
from typing import Any

from assertthat.expr import register
from assertthat.failure import on_failure
from assertthat.objects import (
    Frame,
    Vector,
    dim,
    elements,
    is_missing,
    is_numeric,
    length,
    names,
)
from assertthat.see import assert_that


def _deparse(call: Any, key: str) -> str:
    from assertthat.see import _deparse_one

    return _deparse_one(call[key])


def _attribute(obj: Any, which: str) -> Any:
    if callable(obj) and which in getattr(obj, "__dict__", {}):
        return obj.__dict__[which]
    if isinstance(obj, Vector) and which in obj.attrs:
        return obj.attrs[which]
    if which == "names":
        return names(obj)
    return None


def has_attr(x: Any, which: Any) -> bool:
    return _attribute(x, which) is not None


def _has_attr_fail(call: Any, env: dict[str, Any]) -> str:
    from assertthat.expr import evaluate

    which = evaluate(call["which"], env)
    return f"{_deparse(call, 'x')} does not have attribute {which}"


def has_name(x: Any, which: Any) -> bool:
    have = names(x) or []
    wanted = elements(which) if not isinstance(which, str) else [which]
    if any(is_missing(item) for item in wanted):
        return False
    return all(item in have for item in wanted)


def _has_name_fail(call: Any, env: dict[str, Any]) -> str:
    from assertthat.expr import evaluate

    which = evaluate(call["which"], env)
    values = elements(which) if not isinstance(which, str) else [which]
    shown = "', '".join(str(item) for item in values)
    return f"{_deparse(call, 'x')} does not have all of these name(s): '{shown}'"


def no_na(x: Any) -> bool:
    return not any(is_missing(item) for item in elements(x))


def _no_na_fail(call: Any, env: dict[str, Any]) -> str:
    from assertthat.expr import evaluate

    value = evaluate(call["x"], env)
    count = sum(1 for item in elements(value) if is_missing(item))
    return f"{_deparse(call, 'x')} contains {count} missing values"


def _all_equal_numeric(target: list[float], current: list[float], tolerance: float) -> bool:
    if len(target) != len(current):
        return False
    target_na = [math.isnan(item) for item in target]
    current_na = [math.isnan(item) for item in current]
    if target_na != current_na:
        return False
    keep_target = []
    keep_current = []
    for left, right, missing in zip(target, current, target_na):
        if missing or left == right:
            continue
        keep_target.append(left)
        keep_current.append(right)
    if not keep_target:
        return True
    count = len(keep_target)
    scale = sum(abs(item) for item in keep_target) / count
    if not (math.isfinite(scale) and scale > tolerance):
        scale = 1.0
    difference = sum(abs(left - right) for left, right in zip(keep_target, keep_current)) / (
        count * scale
    )
    return not (math.isnan(difference) or difference > tolerance)


def _numbers(value: Any) -> list[float] | None:
    if isinstance(value, str) or isinstance(value, bool) or value is None or isinstance(value, Vector) and value.mode == "character":
        return None
    if not is_numeric(value) and not isinstance(value, Vector):
        return None
    if isinstance(value, Vector) and value.mode not in ("integer", "double"):
        return None
    converted = []
    for item in elements(value):
        if is_missing(item):
            converted.append(float("nan"))
        else:
            converted.append(float(item))
    return converted


def all_equal(target: Any, current: Any, tolerance: float | None = None, **kwargs: Any) -> bool | str:
    if tolerance is None:
        for key, value in list(kwargs.items()):
            if "tolerance".startswith(key):
                tolerance = value
                break
    if tolerance is None:
        tolerance = math.sqrt(math.ulp(1.0))
    if target is None or current is None:
        return target is current or "NULL mismatch"
    if is_missing(target) or is_missing(current):
        return target == current or "NA mismatch"
    left = _numbers(target)
    right = _numbers(current)
    if left is not None and right is not None:
        return True if _all_equal_numeric(left, right, float(tolerance)) else "numeric mismatch"
    return target == current or "mismatch"


def are_equal(x: Any, y: Any, **kwargs: Any) -> bool:
    result = all_equal(x, y, **kwargs)
    return result is True


def _are_equal_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    return f"{_deparse(call, 'x')} not equal to {_deparse(call, 'y')}"


def is_error(x: Any) -> bool:
    return isinstance(x, TryError)


class TryError(Exception):
    """The object R's try() returns after stop()."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


def is_time(x: Any) -> bool:
    from datetime import datetime

    return isinstance(x, datetime)


def is_date(x: Any) -> bool:
    from datetime import date, datetime

    return type(x) is date and not isinstance(x, datetime)


def _is_error_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    return f"{_deparse(call, 'x')} is not a try-error"


def _is_time_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    return f"{_deparse(call, 'x')} is not a POSIXt date-time object"


def _is_date_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    return f"{_deparse(call, 'x')} is not a Date object"


def has_args(f: Any, args: Any, exact: bool = False) -> bool:
    assert_that("is.function(f)", env={"f": f})
    from assertthat.expr import formals_of

    have = formals_of(f)
    wanted = elements(args) if not isinstance(args, str) else [args]
    if exact:
        return list(wanted) == list(have)
    return all(item in have for item in wanted)


def _has_args_fail(call: Any, env: dict[str, Any]) -> str:
    from assertthat.expr import evaluate

    args = evaluate(call["args"], env)
    values = elements(args) if not isinstance(args, str) else [args]
    shown = ", ".join(str(item) for item in values)
    return f"Function {_deparse(call, 'f')} does not have arguments {shown}"


def has_args_infix(f: Any, args: Any) -> bool:
    """R's ``%has_args%``, which does not carry has_args's failure handler."""
    return has_args(f, args)


def not_empty(x: Any) -> bool:
    size = dim(x)
    if size is None:
        size = (length(x),)
    return all(item != 0 for item in size)


def _not_empty_fail(call: Any, env: dict[str, Any]) -> str:
    del env
    return f"{_deparse(call, 'x')} has an empty dimension"


def install_assertions() -> None:
    register("has_attr", has_attr, ["x", "which"])
    register("%has_attr%", has_attr, ["x", "which"])
    register("has_name", has_name, ["x", "which"])
    register("%has_name%", has_name, ["x", "which"])
    register("noNA", no_na, ["x"])
    register("are_equal", are_equal, ["x", "y", "..."])
    register("is.error", is_error, ["x"])
    register("is.time", is_time, ["x"])
    register("is.date", is_date, ["x"])
    register("has_args", has_args, ["f", "args", "exact"])
    register("%has_args%", has_args_infix, ["f", "args"])
    register("not_empty", not_empty, ["x"])
    on_failure(has_attr, _has_attr_fail)
    on_failure(has_name, _has_name_fail)
    on_failure(no_na, _no_na_fail)
    on_failure(are_equal, _are_equal_fail)
    on_failure(is_error, _is_error_fail)
    on_failure(is_time, _is_time_fail)
    on_failure(is_date, _is_date_fail)
    on_failure(has_args, _has_args_fail)
    on_failure(not_empty, _not_empty_fail)


install_assertions()


def frame(nrow: int, ncol: int) -> Frame:
    return Frame(nrow, ncol)
