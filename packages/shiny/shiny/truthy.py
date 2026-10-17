"""Truthy and falsy values, from shiny 1.14.0 `R/utils.R`."""

from __future__ import annotations

import math

from shiny.values import Missing, ShinyError, Vector, WithClass


def isTruthy(x):
    """Whether `x` counts as supplied.

    A value is truthy unless it is FALSE, NULL, "", an empty atomic vector,
    an atomic vector of only missing values, a logical vector with no TRUE,
    a try-error, or an unclicked action button. Zero is truthy.
    """
    classes = _classes(x)
    value = x.value if isinstance(x, WithClass) else x
    if "try-error" in classes:
        return False
    if value is None:
        return False
    if not _is_atomic(value):
        return True
    data, mode = _atoms(value)
    if len(data) == 0:
        return False
    if all(_is_na(item, mode) for item in data):
        return False
    if mode == "character" and not any(
        _nzchar(item) for item in data if not _is_na(item, mode)
    ):
        return False
    if "shinyActionButtonValue" in classes:
        equal = _equals_zero(data, mode)
        if equal is None:
            raise ShinyError("missing value where TRUE/FALSE needed")
        if equal:
            return False
    if mode == "logical" and not any(
        item is True for item in data if not _is_na(item, mode)
    ):
        return False
    return True


def _classes(value) -> tuple:
    if isinstance(value, WithClass):
        return value.classes
    if isinstance(value, Vector):
        return value.classes
    return ()


def _is_atomic(value) -> bool:
    if isinstance(value, Vector):
        return True
    if isinstance(value, Missing):
        return True
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float, str, complex, bytes, bytearray)):
        return True
    return False


def _atoms(value):
    if isinstance(value, Vector):
        return value.data, value.mode
    if isinstance(value, Missing):
        return [value], value.mode
    if isinstance(value, bool):
        return [value], "logical"
    if isinstance(value, int):
        return [value], "integer"
    if isinstance(value, float):
        return [value], "double"
    if isinstance(value, str):
        return [value], "character"
    if isinstance(value, complex):
        return [value], "complex"
    if isinstance(value, (bytes, bytearray)):
        return list(value), "raw"
    raise ShinyError("non-atomic value")


def _is_na(item, mode: str) -> bool:
    if isinstance(item, Missing):
        return True
    if mode == "double" and isinstance(item, float) and math.isnan(item):
        return True
    if mode == "complex" and isinstance(item, complex):
        return math.isnan(item.real) or math.isnan(item.imag)
    return False


def _nzchar(item) -> bool:
    return isinstance(item, str) and len(item) > 0


def _equals_zero(data, mode: str):
    """R's `x == 0` when that result has to be one logical value."""
    if len(data) != 1:
        raise ShinyError(
            f"'length = {len(data)}' in coercion to 'logical(1)'"
        )
    item = data[0]
    if _is_na(item, mode):
        return None
    if mode == "character":
        # `==` turns the number into "0" and compares strings.
        return item == "0"
    if mode == "logical":
        return item is False
    if mode in ("integer", "double", "complex", "raw"):
        return item == 0
    return False
