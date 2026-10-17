"""R values that the assertions actually distinguish."""

from __future__ import annotations

import math
from typing import Any


class Missing:
    """An R missing value. Logical NA is not numeric, and it is not NaN."""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    def __repr__(self) -> str:
        if self.mode == "logical":
            return "NA"
        if self.mode == "integer":
            return "NA_integer_"
        if self.mode == "character":
            return "NA_character_"
        return "NA_real_"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Missing) and self.mode == other.mode

    def __hash__(self) -> int:
        return hash(("NA", self.mode))


NA = Missing("logical")
NA_integer_ = Missing("integer")
NA_real_ = Missing("double")
NA_character_ = Missing("character")


class Vector:
    """Atomic vector. A Python str is a length-one character vector, not this."""

    def __init__(self, data: list[Any], mode: str) -> None:
        self.data = list(data)
        self.mode = mode
        self.names: list[Any] | None = None
        self.dim: tuple[int, ...] | None = None
        self.attrs: dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"Vector({self.data!r}, {self.mode!r})"


class Frame:
    """A data frame known by its dimension. not_empty only reads dim."""

    def __init__(self, nrow: int, ncol: int) -> None:
        self.dim = (nrow, ncol)


def is_missing(value: Any) -> bool:
    if isinstance(value, Missing):
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def is_null(value: Any) -> bool:
    return value is None


def length(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, Vector):
        return len(value.data)
    if isinstance(value, (list, tuple, dict)):
        return len(value)
    if isinstance(value, Frame):
        return value.dim[0] * value.dim[1]
    return 1


def dim(value: Any) -> tuple[int, ...] | None:
    if isinstance(value, (Vector, Frame)):
        return value.dim
    return None


def names(value: Any) -> list[Any] | None:
    if isinstance(value, dict):
        return list(value.keys())
    if isinstance(value, Vector):
        return value.names
    return None


def mode_of(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, Vector):
        return value.mode
    if isinstance(value, Missing):
        return value.mode
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, str):
        return "character"
    if isinstance(value, int):
        return "double"
    if isinstance(value, float):
        return "double"
    if isinstance(value, dict):
        return "list"
    return "other"


def is_logical(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, Missing):
        return value.mode == "logical"
    if isinstance(value, Vector):
        return value.mode == "logical"
    return False


def is_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, Missing):
        return value.mode in ("integer", "double")
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, Vector):
        return value.mode in ("integer", "double")
    return False


def is_integer_mode(value: Any) -> bool:
    if isinstance(value, Missing):
        return value.mode == "integer"
    if isinstance(value, Vector):
        return value.mode == "integer"
    return False


def is_character(value: Any) -> bool:
    if isinstance(value, str):
        return True
    if isinstance(value, Missing):
        return value.mode == "character"
    if isinstance(value, Vector):
        return value.mode == "character"
    return False


def elements(value: Any) -> list[Any]:
    if isinstance(value, Vector):
        return list(value.data)
    if value is None:
        return []
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def as_number(value: Any) -> float:
    if isinstance(value, Missing) or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    if isinstance(value, bool):
        return float(value)
    return float(value)


def r_all(flags: list[Any]) -> Any:
    """all() of a logical vector. NA is Missing('logical')."""
    saw_na = False
    for flag in flags:
        if flag is False:
            return False
        if is_missing(flag):
            saw_na = True
        elif flag is not True:
            return False
    return NA if saw_na else True


def r_and(left: Any, right: Any) -> Any:
    """Scalar &&, including NA && FALSE == FALSE."""
    if left is False:
        return False
    if is_missing(left):
        return False if right is False else NA
    if right is True:
        return True
    if right is False:
        return False
    return NA
