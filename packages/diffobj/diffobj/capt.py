"""Text representations: R print, str, deparse, files, and CSV."""

from __future__ import annotations

import csv
import re
from pathlib import Path

_ATOM_HEADER = re.compile(r"^\s*\[[1-9][0-9]*\]\s")


class Call:
    """A language object ``deparse`` renders as ``name(arg, arg)``."""

    def __init__(self, name: str, *args):
        self.name = name
        self.args = args

    def __repr__(self) -> str:
        rendered = ", ".join(_atom_text(arg) for arg in self.args)
        return f"{self.name}({rendered})"


class DataFrame:
    """A small data frame: column names and row-wise values."""

    def __init__(self, columns: dict[str, list], row_names: list[str] | None = None):
        self.columns = {name: list(values) for name, values in columns.items()}
        nrow = len(next(iter(self.columns.values()))) if self.columns else 0
        self.row_names = list(row_names) if row_names is not None else [str(i) for i in range(1, nrow + 1)]

    @property
    def dim(self):
        ncol = len(self.columns)
        nrow = len(self.row_names)
        return (nrow, ncol)


def _atom_text(value) -> str:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, float):
        if value != value:
            return "NaN"
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return repr(value)
    return str(value)


def _is_atomic_vector(value) -> bool:
    if isinstance(value, (str, bytes)) or isinstance(value, (DataFrame, Call, dict)):
        return False
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, (str, int, float, bool)) or item is None for item in value)
    return isinstance(value, (str, int, float, bool)) or value is None


def _as_vector(value) -> list:
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _index_width(count: int) -> int:
    return len(f"[{max(count, 1)}]")


def _fit_lines(labels: list[str], width: int) -> list[str]:
    if not labels:
        return []
    count = len(labels)
    gutter = _index_width(count)
    lines = []
    index = 0
    while index < count:
        line = f"[{index + 1}]".rjust(gutter)
        first = True
        while index < count:
            piece = labels[index]
            extra = 1 + len(piece)
            if not first and len(line) + extra > width:
                break
            line += " " + piece
            index += 1
            first = False
            if len(line) >= width:
                break
        lines.append(line)
    return lines


def _format_numbers(values: list) -> list[str]:
    logical = any(isinstance(item, bool) for item in values)
    if logical:
        text = []
        for item in values:
            if item is None:
                text.append("NA")
            elif item is True:
                text.append("TRUE")
            elif item is False:
                text.append("FALSE")
            else:
                text.append(_atom_text(item))
        width = max(len(item) for item in text)
        return [item.rjust(width) for item in text]
    if any(isinstance(item, float) for item in values):
        shown = []
        for item in values:
            if item is None:
                shown.append("NA")
            elif isinstance(item, float) and item == int(item) and abs(item) < 1e15:
                shown.append(f"{int(item)}.0" if any(
                    isinstance(other, float) and other != int(other) for other in values if other is not None
                ) else str(int(item)))
            else:
                shown.append(_atom_text(item))
        # Common decimal width like R's format for a mix of 1.5 and 2.
        if any(isinstance(item, float) and item is not None and item != int(item) for item in values):
            shown = []
            for item in values:
                if item is None:
                    shown.append("NA")
                elif isinstance(item, (int, float)) and not isinstance(item, bool):
                    shown.append(f"{float(item):.1f}" if _one_decimal(values) else _atom_text(float(item)))
                else:
                    shown.append(_atom_text(item))
        width = max(len(item) for item in shown) if shown else 0
        return [item.rjust(width) for item in shown]
    text = ["NA" if item is None else str(item) for item in values]
    width = max((len(item) for item in text), default=0)
    return [item.rjust(width) for item in text]


def _one_decimal(values) -> bool:
    for item in values:
        if isinstance(item, float) and item == item and item != int(item):
            scaled = item * 10
            if scaled != int(scaled):
                return False
    return True


def r_print(value, width: int) -> list[str]:
    """``print`` for atomic vectors and a small data frame."""

    if isinstance(value, DataFrame) or _is_frame(value):
        return _print_frame(value, width)
    if isinstance(value, dict):
        return r_str(value, width)
    vector = _as_vector(value)
    if not vector:
        return ["NULL"]
    if all(isinstance(item, str) or item is None for item in vector):
        labels = ["NA" if item is None else _atom_text(item) for item in vector]
        return _fit_lines(labels, width)
    labels = _format_numbers(vector)
    return _fit_lines(labels, width)


def _is_frame(value) -> bool:
    return isinstance(value, dict) and value and all(isinstance(item, (list, tuple)) for item in value.values())


def _print_frame(value, width: int) -> list[str]:
    if isinstance(value, DataFrame):
        columns = value.columns
        row_names = value.row_names
    else:
        columns = {name: list(items) for name, items in value.items()}
        nrow = len(next(iter(columns.values()))) if columns else 0
        row_names = [str(i) for i in range(1, nrow + 1)]
    formatted = {}
    for name, items in columns.items():
        if all(isinstance(item, str) or item is None for item in items):
            text = ["NA" if item is None else str(item) for item in items]
            size = max([len(name), *(len(item) for item in text)])
            formatted[name] = [item.ljust(size) for item in text]
        else:
            nums = _format_numbers(items)
            size = max([len(name), *(len(item) for item in nums)])
            formatted[name] = [item.rjust(size) for item in nums]
    name_width = max(len(name) for name in row_names) if row_names else 0
    header = " " * name_width
    for name, items in formatted.items():
        size = len(items[0]) if items else len(name)
        numeric = not all(isinstance(item, str) or item is None for item in columns[name])
        shown = name.rjust(size) if numeric else name.ljust(size)
        header += " " + shown
    lines = [header.rstrip()]
    for row, row_name in enumerate(row_names):
        line = row_name.rjust(name_width)
        for items in formatted.values():
            line += " " + items[row]
        lines.append(line.rstrip())
    return lines


def r_str(value, width: int = 80) -> list[str]:
    """``utils::str`` for a small named list of atomic values."""

    if not isinstance(value, dict):
        vector = _as_vector(value)
        kind = _str_kind(vector)
        body = " ".join(_str_atom(item) for item in vector[:3])
        return [f" {kind} {body}".rstrip()]
    lines = [f"List of {len(value)}"]
    for name, item in value.items():
        if isinstance(item, dict):
            lines.append(f" $ {name}:List of {len(item)}")
            for child, child_value in item.items():
                lines.append(f"  ..$ {child}: {_str_scalar(child_value)}")
        else:
            lines.append(f" $ {name}: {_str_scalar(item)}")
    return lines


def _str_kind(vector: list) -> str:
    if all(isinstance(item, bool) or item is None for item in vector):
        return "logi"
    if all(isinstance(item, str) or item is None for item in vector):
        return "chr"
    if all(isinstance(item, int) and not isinstance(item, bool) or item is None for item in vector):
        return "num"
    return "num"


def _str_atom(item) -> str:
    if item is None:
        return "NA"
    if isinstance(item, str):
        return _atom_text(item)
    if isinstance(item, bool):
        return "TRUE" if item else "FALSE"
    if isinstance(item, float):
        if item == int(item) and abs(item) < 1e15:
            return str(int(item))
        return _atom_text(item)
    return str(item)


def _str_scalar(item) -> str:
    if isinstance(item, (list, tuple)):
        kind = _str_kind(list(item))
        shown = " ".join(_str_atom(part) for part in list(item)[:4])
        return f"{kind} {shown}".rstrip()
    if isinstance(item, bool):
        return f"logi {'TRUE' if item else 'FALSE'}"
    if isinstance(item, str):
        return f"chr {_atom_text(item)}"
    if isinstance(item, float):
        shown = str(int(item)) if item == int(item) and abs(item) < 1e15 else _atom_text(item)
        return f"num {shown}"
    if isinstance(item, int):
        return f"num {item}"
    return f"chr {_atom_text(str(item))}"


def r_deparse(value, width: int = 80) -> list[str]:
    """``deparse`` for a call or a short atomic vector."""

    if isinstance(value, Call):
        return [str(value)]
    if isinstance(value, (list, tuple)):
        if (
            len(value) >= 2
            and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
            and list(value) == list(range(value[0], value[-1] + 1))
        ):
            return [f"{value[0]}:{value[-1]}"]
        body = ", ".join(_atom_text(item) for item in value)
        text = f"c({body})"
        if len(text) <= width:
            return [text]
        lines = []
        current = "c("
        for offset, item in enumerate(value):
            piece = _atom_text(item)
            extra = (", " if current not in ("c(",) else "") + piece
            if len(current) + len(extra) > width and current != "c(":
                lines.append(current)
                current = "  " + piece
            else:
                current += extra if current != "c(" else piece
        if not current.endswith(")"):
            current += ")"
        lines.append(current)
        return lines
    return [str(value)]


def read_lines(path) -> list[str]:
    try:
        return Path(path).read_text().splitlines()
    except OSError as exc:
        raise OSError(str(exc)) from exc


def read_csv_frame(path) -> DataFrame:
    with Path(path).open(newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return DataFrame({})
    header = rows[0]
    body = rows[1:]
    columns = {name: [] for name in header}
    for row in body:
        for name, cell in zip(header, row):
            columns[name].append(_csv_cell(cell))
    return DataFrame(columns)


def _csv_cell(cell: str):
    if cell == "":
        return None
    try:
        if any(char in cell for char in ".eE"):
            value = float(cell)
            if value == int(value) and "e" not in cell.lower() and "." not in cell:
                return int(value)
            if value == int(value) and "." not in cell:
                return int(value)
            return value
        return int(cell)
    except ValueError:
        return cell


def atomic_row_headers(lines: list[str]) -> list[int]:
    """1-based indices of ``[1]`` / ``[9]`` headers, or empty."""

    flags = [bool(_ATOM_HEADER.match(line)) for line in lines]
    if not any(flags):
        return []
    start = flags.index(True)
    end = start
    while end < len(flags) and flags[end]:
        end += 1
    block = list(range(start, end))
    headers = [_ATOM_HEADER.match(lines[index]).group(0) for index in block]
    if len({len(item) for item in headers}) != 1:
        return []
    numbers = [int(re.search(r"[0-9]+", item).group(0)) for item in headers]
    if numbers[0] != 1:
        return []
    if len(numbers) > 1:
        gaps = {numbers[i + 1] - numbers[i] for i in range(len(numbers) - 1)}
        if len(gaps) != 1:
            return []
    return [index + 1 for index in block]


def trim_atomic(lines: list[str]) -> list[tuple[int, int]]:
    headers = set(atomic_row_headers(lines))
    spans = []
    for index, line in enumerate(lines, 1):
        if index in headers:
            match = _ATOM_HEADER.match(line)
            start = match.end() + 1  # 1-based index of the first kept character
            spans.append((start, len(line)))
        else:
            spans.append((1, len(line)))
    return spans


def has_dim(value) -> bool:
    return isinstance(value, DataFrame) or _is_frame(value)
