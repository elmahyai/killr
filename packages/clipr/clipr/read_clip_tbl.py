"""Parse clipboard text into a data frame."""

from __future__ import annotations

import math
import re
from typing import Any

from clipr._render import Frame, make_names
from clipr.read_clip import read_clip

_MISSING = object()
_INT = re.compile(r"[+-]?\d+")
_FLOAT = re.compile(r"[+-]?((\d+(\.\d*)?)|(\.\d+))([eE][+-]?\d+)?")
_SPECIAL = {"Inf": math.inf, "-Inf": -math.inf, "NaN": math.nan}


def read_clip_tbl(x: Any = _MISSING, **options: Any) -> Frame | None:
    """Read clipboard text as a table.

    Defaults match clipr: header, tab separator, strings kept as text, missing
    values NA and blank, surrounding whitespace stripped, and quoting off.
    A leading tab on the first line makes the first column the row names.
    An empty clipboard returns None. Extra options are read.table arguments.
    allow_non_interactive is not one of them; set CLIPR_ALLOW to read the
    live clipboard from a non-interactive session.
    """

    if "allow_non_interactive" in options:
        raise TypeError("unused argument (allow_non_interactive)")
    if x is _MISSING:
        x = read_clip()
    if x is None:
        return None
    if isinstance(x, str):
        lines = [x]
    else:
        lines = ["" if item is None else str(item) for item in x]
    return _read_table(lines, options)


def _read_table(lines: list[str], options: dict) -> Frame:
    header = True if options.get("header") is None else bool(options["header"])
    sep = "\t" if options.get("sep") is None else options["sep"]
    na_strings = options.get("na.strings", options.get("na_strings", ["NA", ""]))
    strip = True if options.get("strip.white", options.get("strip_white", True)) else False
    row_spec = options.get("row.names", _MISSING)
    if row_spec is _MISSING:
        row_spec = options.get("row_names", _MISSING)
    if row_spec is _MISSING or row_spec is None:
        row_spec = 1 if lines and lines[0][:1] == "\t" else None
    records = []
    for line in lines:
        fields = line.split(sep)
        if strip:
            fields = [field.strip() for field in fields]
        records.append(fields)
    names = None
    body = records
    if header and records:
        names = records[0]
        body = records[1:]
    row_names = None
    if row_spec == 1:
        if names is not None:
            names = names[1:]
        row_names = [row[0] if row else "" for row in body]
        body = [row[1:] if row else [] for row in body]
    width = max([len(names or [])] + [len(row) for row in body], default=0)
    if names is None:
        names = [f"V{index}" for index in range(1, width + 1)]
    else:
        names = list(names) + [""] * (width - len(names))
    names = make_names(names, unique=True)
    raw = [[] for _ in names]
    for row in body:
        padded = list(row) + [""] * (len(names) - len(row))
        for index, cell in enumerate(padded[: len(names)]):
            raw[index].append(cell)
    columns = {
        name: _convert_column(cells, list(na_strings))
        for name, cells in zip(names, raw)
    }
    return Frame(columns, row_names=row_names)


def _convert_column(cells: list[str], na_strings: list[str]) -> list:
    missing = set(na_strings)
    kinds: list[str] = []
    parsed: list[Any] = []
    for cell in cells:
        if cell in missing:
            parsed.append(None)
            continue
        if cell in _SPECIAL:
            parsed.append(_SPECIAL[cell])
            kinds.append("float")
            continue
        if _INT.fullmatch(cell) and _fits_integer(cell):
            parsed.append(int(cell))
            kinds.append("int")
            continue
        if _FLOAT.fullmatch(cell):
            parsed.append(float(cell))
            kinds.append("float")
            continue
        parsed.append(cell)
        kinds.append("str")
    if "str" in kinds:
        return [None if value is None else str(value) if not isinstance(value, str) else value for value in parsed]
    if "float" in kinds:
        return [None if value is None else float(value) for value in parsed]
    return parsed


def _fits_integer(cell: str) -> bool:
    number = int(cell)
    return -2147483647 <= number <= 2147483647
