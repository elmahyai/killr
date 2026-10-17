"""Columns and data frames used by the reshape2 translation.

A column keeps an R storage mode. Missing values are ``None``. A real
``NaN`` stays a float, because R prints that as ``NaN`` and prints a
missing real as ``NA``. Factors are integer codes with a ``levels``
attribute. Codes are 1-based.
"""

from __future__ import annotations

import math
from typing import Any


_STORAGES = ("logical", "integer", "double", "complex", "character", "raw", "list")
_RANK = {"logical": 10, "integer": 13, "double": 14, "complex": 15, "character": 16, "raw": 24}


class Column:
    """One atomic column, or a list column."""

    def __init__(self, storage: str, values: Any, attributes: dict | None = None):
        if storage not in _STORAGES:
            raise ValueError(f"unknown storage mode {storage!r}")
        self.storage = storage
        self.values = list(values)
        self.attributes = dict(attributes or {})

    def __len__(self) -> int:
        return len(self.values)

    def copy(self) -> "Column":
        return Column(self.storage, list(self.values), dict(self.attributes))


class DataFrame:
    """A data frame with columns in order. Duplicate names are kept."""

    def __init__(self, columns: Any = (), nrows: int | None = None):
        self.columns: list[tuple[str, Column]] = []
        if isinstance(columns, dict):
            pairs = list(columns.items())
        else:
            pairs = list(columns)
        for name, column in pairs:
            if not isinstance(column, Column):
                column = as_column(column)
            self.columns.append((str(name), column))
        if self.columns:
            lengths = {len(column) for _, column in self.columns}
            if len(lengths) != 1:
                raise ValueError("arguments imply differing number of rows")
            self.nrows = len(self.columns[0][1])
        else:
            self.nrows = 0 if nrows is None else int(nrows)

    def column(self, name: str) -> Column | None:
        for key, column in self.columns:
            if key == name:
                return column
        return None

    def names(self) -> list[str]:
        return [name for name, _ in self.columns]

    def copy(self) -> "DataFrame":
        return DataFrame([(name, column.copy()) for name, column in self.columns], nrows=self.nrows)


def is_na(value: Any) -> bool:
    """True for R's missing value, including a stringi ``NA`` object."""

    if value is None:
        return True
    return type(value).__name__ == "NAType"


def is_factor(column: Column) -> bool:
    classes = class_vector(column)
    return "factor" in classes


def is_posixlt(column: Column) -> bool:
    return "POSIXlt" in class_vector(column)


def class_vector(column: Column) -> list[str]:
    value = column.attributes.get("class")
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def factor(labels: Any, levels: Any = None) -> Column:
    """Build a factor from labels. ``levels`` defaults to first-seen order."""

    text: list[Any] = []
    for label in labels:
        text.append(None if is_na(label) else str(label))
    if levels is None:
        stored: list[str] = []
        seen: set[str] = set()
        for label in text:
            if label is None or label in seen:
                continue
            seen.add(label)
            stored.append(label)
    else:
        stored = [str(level) for level in levels]
    index = {level: code for code, level in enumerate(stored, start=1)}
    codes = []
    for label in text:
        if label is None:
            codes.append(None)
        elif label not in index:
            codes.append(None)
        else:
            codes.append(index[label])
    return Column("integer", codes, {"levels": stored, "class": "factor"})


def factor_labels(column: Column) -> list[Any]:
    levels = [str(level) for level in column.attributes.get("levels", [])]
    labels = []
    for code in column.values:
        if code is None:
            labels.append(None)
        else:
            labels.append(levels[int(code) - 1])
    return labels


def as_column(values: Any) -> Column:
    """Infer a column from a Python sequence, a factor column, or a scalar."""

    if isinstance(values, Column):
        return values.copy()
    if isinstance(values, str) or is_na(values):
        values = [values]
    elif not isinstance(values, (list, tuple)):
        try:
            import numpy as np

            if isinstance(values, np.ndarray):
                values = values.tolist()
            else:
                values = [values]
        except ImportError:
            values = [values]
    return _infer(list(values))


def _infer(values: list[Any]) -> Column:
    kinds = set()
    for value in values:
        if is_na(value):
            continue
        if isinstance(value, bool) or type(value).__name__ == "bool_":
            kinds.add("logical")
        elif _is_int(value):
            kinds.add("integer")
        elif _is_float(value):
            kinds.add("double")
        elif isinstance(value, complex):
            kinds.add("complex")
        elif isinstance(value, str):
            kinds.add("character")
        else:
            kinds.add("list")
    if "list" in kinds:
        return Column("list", values)
    if "character" in kinds:
        return Column("character", [None if is_na(value) else str(value) for value in values])
    if "complex" in kinds:
        return Column("complex", [_as_complex(value) for value in values])
    if "double" in kinds:
        return Column("double", [_as_float(value) for value in values])
    if "integer" in kinds:
        return Column("integer", [_as_int(value) for value in values])
    if "logical" in kinds:
        return Column("logical", [None if is_na(value) else bool(value) for value in values])
    return Column("logical", [None for _ in values])


def _is_int(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    name = type(value).__name__
    return name.startswith("int") or name.startswith("uint")


def _is_float(value: Any) -> bool:
    return isinstance(value, float) or _is_numpy_float(value)


def _is_numpy_float(value: Any) -> bool:
    return type(value).__name__ in {"float64", "float32", "float16"} or (
        hasattr(value, "dtype") and "float" in str(getattr(value, "dtype", ""))
    )


def _as_int(value: Any) -> int | None:
    if is_na(value):
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    return int(value)


def _as_float(value: Any) -> float | None:
    if is_na(value):
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(value)


def _as_complex(value: Any) -> complex | None:
    if is_na(value):
        return None
    if isinstance(value, bool):
        return complex(1.0 if value else 0.0, 0.0)
    if isinstance(value, complex):
        return value
    return complex(float(value), 0.0)


def na_value(storage: str) -> Any:
    return None


def is_missing_value(value: Any, storage: str) -> bool:
    """R's ``is.na``. A real or complex ``NaN`` counts as missing."""

    if is_na(value):
        return True
    if storage == "double" and isinstance(value, float) and math.isnan(value):
        return True
    if storage == "complex" and isinstance(value, complex):
        return math.isnan(value.real) or math.isnan(value.imag)
    return False


def promote(left: str, right: str) -> str:
    if left == right:
        return left
    if left == "list" or right == "list":
        return "list"
    return left if _RANK[left] >= _RANK[right] else right


def coerce_value(value: Any, source: str, target: str) -> Any:
    if source == target:
        return value
    if is_na(value):
        return None
    if target == "character":
        return _as_character(value, source)
    if target == "complex":
        return _as_complex(value)
    if target == "double":
        number = _as_float(value)
        return number
    if target == "integer":
        return _as_int(value)
    if target == "logical":
        if value is None:
            return None
        return bool(value)
    return value


def _as_character(value: Any, source: str) -> str | None:
    if is_na(value):
        return None
    if source == "logical" or isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if source == "integer" or _is_int(value):
        return str(int(value))
    if source == "double" or isinstance(value, float):
        number = float(value)
        if math.isnan(number):
            return "NaN"
        if math.isinf(number):
            return "Inf" if number > 0 else "-Inf"
        return _format_real(number)
    if source == "complex" or isinstance(value, complex):
        return _format_complex(value)
    return str(value)


def _format_real(value: float) -> str:
    if value == 0:
        return "0"
    text = format(value, ".15g")
    if "e" in text:
        mantissa, exponent = text.split("e")
        return f"{mantissa}e{int(exponent):+03d}"
    return text


def _format_complex(value: complex) -> str:
    real = _format_real(value.real)
    imag = value.imag
    if imag < 0:
        return f"{real}-{_format_real(-imag)}i"
    return f"{real}+{_format_real(imag)}i"


def type_rank(storage: str, column: Column, factors_as_strings: bool) -> int:
    if is_factor(column) and factors_as_strings:
        return _RANK["character"]
    return _RANK.get(storage, 0)


def attributes_equal(left: Column, right: Column) -> bool:
    return _attr_key(left) == _attr_key(right)


def _attr_key(column: Column) -> tuple:
    items = []
    for key, value in column.attributes.items():
        if isinstance(value, list):
            value = tuple(value)
        items.append((key, value))
    return tuple(items)


def repeat_vector(values: list[Any], times: int) -> list[Any]:
    if times == 0:
        return []
    out: list[Any] = []
    for _ in range(times):
        out.extend(values)
    return out


def repeat_each(values: list[Any], each: int) -> list[Any]:
    out: list[Any] = []
    for value in values:
        out.extend([value] * each)
    return out
