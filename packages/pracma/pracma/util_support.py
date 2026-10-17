"""Shared checks for the pracma utility ports."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PracmaError(message)


def match_arg(value, choices):
    """R match.arg: exact match, then a unique prefix. NULL is the first choice."""
    if value is None or isinstance(value, (list, tuple)):
        return choices[0]
    text = str(value)
    exact = [choice for choice in choices if choice == text]
    if len(exact) == 1:
        return exact[0]
    partial = [choice for choice in choices if choice.startswith(text)]
    if len(partial) == 1:
        return partial[0]
    quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices)
    raise PracmaError(f"'arg' should be one of {quoted}")


def is_numeric(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return False
    if value is None:
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    if isinstance(value, (list, tuple)):
        return len(value) == 0 or all(is_numeric(item) for item in value)
    array = np.asarray(value)
    if array.dtype == object or array.dtype == bool:
        return False
    return np.issubdtype(array.dtype, np.number) and not np.iscomplexobj(array)


def is_numeric_or_complex(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (complex, np.complexfloating)):
        return True
    if value is None:
        return False
    array = np.asarray(value)
    if array.dtype == object or array.dtype == bool:
        return False
    return np.issubdtype(array.dtype, np.number)


def as_float(value) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    return array


def char_list(value, message: str) -> list:
    if isinstance(value, str):
        return [value]
    if isinstance(value, np.ndarray) and value.dtype.kind in "US":
        return [str(item) for item in value.reshape(-1)]
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return list(value)
    raise PracmaError(message)


def one_string(value, message: str) -> str:
    items = char_list(value, message)
    if len(items) != 1:
        raise PracmaError(message)
    return items[0]


def r_length(value) -> int:
    if value is None:
        return 0
    return int(np.asarray(value).size)


def is_vector(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes)):
        return True
    array = np.asarray(value)
    return array.ndim <= 1


def is_matrix(value) -> bool:
    if isinstance(value, (str, bytes)) or value is None:
        return False
    return np.asarray(value).ndim == 2


def whole_number(value) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and math.floor(number) == math.ceil(number)


def r_seq(start, stop, count) -> np.ndarray:
    """Equally spaced points, including both ends, matching seq(length.out=)."""
    count = int(count)
    if count <= 1:
        return np.array([float(stop if count == 1 else start)], dtype=float)
    index = np.arange(count, dtype=float)
    values = float(start) + (float(stop) - float(start)) * (index / (count - 1))
    values[-1] = float(stop)
    return values


def flatten_numeric(value) -> np.ndarray:
    if value is None:
        return np.array([])
    array = np.asarray(value)
    if array.dtype == bool:
        array = array.astype(float)
    if np.iscomplexobj(array):
        array = np.real(array)
    return np.array(array, dtype=float).reshape(-1, order="F")


def column_major(data, rows, cols) -> np.ndarray:
    return np.asarray(data, dtype=float).reshape((rows, cols), order="F")
