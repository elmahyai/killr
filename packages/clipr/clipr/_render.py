"""Render values the way clipr prepares text for the clipboard."""

from __future__ import annotations

import math
import warnings
from typing import Any


class Frame:
    """A data frame: named columns of equal length, and optional row names."""

    def __init__(
        self,
        columns: dict[str, list],
        row_names: list[str] | None = None,
    ) -> None:
        self.columns = {str(key): list(value) for key, value in columns.items()}
        lengths = {len(value) for value in self.columns.values()}
        if len(lengths) > 1:
            raise ValueError("columns must have the same length")
        self.row_names = None if row_names is None else [str(name) for name in row_names]
        count = next(iter(lengths), 0)
        if self.row_names is not None and len(self.row_names) != count:
            raise ValueError("row_names must have one name per row")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Frame):
            return NotImplemented
        return self.columns == other.columns and self.row_names == other.row_names

    def __repr__(self) -> str:
        return f"Frame(columns={self.columns!r}, row_names={self.row_names!r})"


class Matrix:
    """A matrix stored by row, with optional dimnames."""

    def __init__(
        self,
        data: list[list],
        row_names: list[str] | None = None,
        col_names: list[str] | None = None,
    ) -> None:
        self.data = [list(row) for row in data]
        self.row_names = None if row_names is None else [str(name) for name in row_names]
        self.col_names = None if col_names is None else [str(name) for name in col_names]


_RESERVED = {
    "if",
    "else",
    "repeat",
    "while",
    "function",
    "for",
    "in",
    "next",
    "break",
    "TRUE",
    "FALSE",
    "NULL",
    "Inf",
    "NaN",
    "NA",
    "NA_integer_",
    "NA_real_",
    "NA_complex_",
    "NA_character_",
    "...",
}


def r_character_double(value: float) -> str:
    """Match R's as.character for a double.

    Fifteen significant digits. Scientific notation is used when that form is
    shorter than fixed notation. A tie keeps the fixed form. The exponent
    carries a sign and at least two digits.
    """

    if math.isnan(value):
        return "NA"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def make_names(names: list[Any], unique: bool = False, allow_: bool = True) -> list[str]:
    """Match R's make.names for column headers from read.table."""

    fixed = [_one_name(name, allow_) for name in names]
    if unique:
        return _make_unique(fixed)
    return fixed


def _one_name(name: Any, allow_: bool) -> str:
    if name is None or (isinstance(name, float) and math.isnan(name)):
        text = "NA"
    else:
        text = str(name)
    allowed = []
    for char in text:
        if char.isalnum() or char == "." or (allow_ and char == "_"):
            allowed.append(char)
        else:
            allowed.append(".")
    cleaned = "".join(allowed)
    if cleaned == "" or cleaned[0].isdigit() or (
        cleaned[0] == "." and len(cleaned) > 1 and cleaned[1].isdigit()
    ):
        cleaned = "X" + cleaned
    if cleaned in _RESERVED:
        cleaned = cleaned + "."
    return cleaned


def _make_unique(names: list[str], sep: str = ".") -> list[str]:
    seen: dict[str, int] = {}
    used: set[str] = set()
    result = []
    for name in names:
        if name not in used:
            used.add(name)
            seen[name] = 0
            result.append(name)
            continue
        index = seen.get(name, 0)
        while True:
            index += 1
            candidate = f"{name}{sep}{index}"
            if candidate not in used:
                break
        seen[name] = index
        used.add(candidate)
        result.append(candidate)
    return result


def _is_column_dict(content: Any) -> bool:
    if not isinstance(content, dict) or not content:
        return False
    lengths = []
    for key, value in content.items():
        if isinstance(value, (str, bytes)) or isinstance(key, (list, dict)):
            return False
        try:
            lengths.append(len(value))
        except TypeError:
            return False
    return len(set(lengths)) == 1


def _is_matrix(content: Any) -> bool:
    if not isinstance(content, (list, tuple)) or not content:
        return False
    if not all(isinstance(row, (list, tuple)) for row in content):
        return False
    width = len(content[0])
    return all(len(row) == width for row in content)


def is_table(content: Any) -> bool:
    return isinstance(content, (Frame, Matrix)) or _is_column_dict(content) or _is_matrix(content)


def match_object_type(object_type: str) -> str:
    choices = ("auto", "character", "table")
    if object_type in choices:
        return object_type
    matches = [choice for choice in choices if choice.startswith(object_type)]
    if len(matches) == 1:
        return matches[0]
    quoted = ", ".join(repr(choice) for choice in choices)
    raise ValueError(f"'{object_type}' should be one of {quoted}")


def render_object(content: Any, object_type: str, breaks: str, dots: dict) -> str:
    if object_type == "auto":
        object_type = "table" if is_table(content) else "character"
    if object_type == "table":
        return table_str(content, breaks, dots)
    return flat_str(content, breaks)


def flat_str(content: Any, breaks: str) -> str:
    values = _character_vector(content)
    if len(values) < 1:
        return ""
    if len(values) > 1:
        return breaks.join(values)
    return values[0]


def _character_vector(content: Any) -> list[str]:
    if content is None:
        warnings.warn("Coercing content to character", stacklevel=4)
        return []
    if isinstance(content, str):
        return [content]
    if isinstance(content, bool):
        warnings.warn("Coercing content to character", stacklevel=4)
        return ["TRUE" if content else "FALSE"]
    if isinstance(content, int):
        warnings.warn("Coercing content to character", stacklevel=4)
        return [str(content)]
    if isinstance(content, float):
        warnings.warn("Coercing content to character", stacklevel=4)
        if math.isnan(content):
            return ["NA"]
        return [r_character_double(content)]
    if isinstance(content, (list, tuple)) and not _is_matrix(content):
        if len(content) == 0:
            return []
        values = []
        coerce = False
        for item in content:
            if isinstance(item, str):
                values.append(item)
            else:
                coerce = True
                values.append(_scalar_character(item))
        if coerce:
            warnings.warn("Coercing content to character", stacklevel=4)
        return values
    warnings.warn("Coercing content to character", stacklevel=4)
    return [_scalar_character(content)]


def _scalar_character(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return r_character_double(value)
    return str(value)


def table_str(content: Any, breaks: str, dots: dict) -> str:
    rows, col_names, row_names, has_col_names = _table_parts(content)
    sep = "\t" if dots.get("sep") is None else dots["sep"]
    quote = False if dots.get("quote") is None else bool(dots["quote"])
    na = "" if dots.get("na") is None else str(dots["na"])
    write_cols, header = _column_flag(dots, col_names, has_col_names, len(rows[0]) if rows else 0)
    write_rows, names = _row_flag(dots, row_names, len(rows))
    lines = []
    if write_cols:
        lines.append(sep.join(_format_name(name, quote) for name in header))
    for index, row in enumerate(rows):
        cells = [_format_cell(value, na, quote) for value in row]
        if write_rows:
            cells.insert(0, _format_name(names[index], quote))
        lines.append(sep.join(cells))
    rendered = breaks.join(lines)
    if write_rows and write_cols:
        rendered = f"{sep}{rendered}"
    return rendered


def _table_parts(content: Any) -> tuple[list[list], list[str] | None, list[str] | None, bool]:
    if isinstance(content, Frame):
        names = list(content.columns)
        count = len(next(iter(content.columns.values()))) if names else 0
        rows = [[content.columns[name][index] for name in names] for index in range(count)]
        return rows, names, content.row_names, True
    if isinstance(content, Matrix):
        return content.data, content.col_names, content.row_names, content.col_names is not None
    if _is_column_dict(content):
        names = [str(key) for key in content]
        count = len(next(iter(content.values()))) if names else 0
        rows = [[content[key][index] for key in content] for index in range(count)]
        return rows, names, None, True
    if _is_matrix(content):
        return [list(row) for row in content], None, None, False
    raise TypeError("table rendering expects a data frame or matrix")


def _column_flag(dots: dict, col_names: list[str] | None, has_col_names: bool, width: int):
    spec = dots.get("col.names", dots.get("col_names", None))
    if "col.names" not in dots and "col_names" not in dots:
        spec = None
    if spec is None:
        if not has_col_names:
            return False, []
        return True, list(col_names or [])
    if spec is False:
        return False, []
    if spec is True:
        if col_names is not None:
            return True, list(col_names)
        return True, [f"V{index}" for index in range(1, width + 1)]
    if isinstance(spec, (list, tuple)):
        return True, [str(name) for name in spec]
    return bool(spec), list(col_names or [])


def _row_flag(dots: dict, row_names: list[str] | None, count: int):
    if "row.names" in dots:
        spec = dots["row.names"]
    elif "row_names" in dots and isinstance(dots["row_names"], bool):
        spec = dots["row_names"]
    else:
        spec = None
    if spec is None:
        numbered = row_names is None or row_names == [str(index) for index in range(1, count + 1)]
        spec = False if numbered else True
    if spec is False or spec is None:
        return False, []
    if spec is True:
        names = row_names if row_names is not None else [str(index) for index in range(1, count + 1)]
        return True, names
    if isinstance(spec, (list, tuple)):
        return True, [str(name) for name in spec]
    return bool(spec), row_names or [str(index) for index in range(1, count + 1)]


def _format_cell(value: Any, na: str, quote: bool) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return na
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return r_character_double(value)
    return _format_name(str(value), quote)


def _format_name(value: str, quote: bool) -> str:
    if not quote:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
