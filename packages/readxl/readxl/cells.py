"""Cell rectangles re-exported by readxl from cellranger.

cellranger is not a registry package. These four functions are readxl exports,
and ``as_cell_limits`` is what ``read_excel`` uses to read a range string.
"""

from __future__ import annotations

import re
from collections.abc import Sequence


_A1 = re.compile(r"^\$?[A-Za-z]{1,3}\$?[0-9]{1,5}$")
_R1C1 = re.compile(r"^R\[?\-?[0-9]*\]?C\[?\-?[0-9]*\]?$")
_A1_PARTS = re.compile(
    r"(?P<col_abs>\$?)(?P<col_ref>[A-Za-z]{1,3})(?P<row_abs>\$?)(?P<row_ref>[0-9]+)"
)
_R1C1_PARTS = re.compile(
    r"^R(?P<row_abs>\[?)(?P<row_ref>[0-9\-]*)(?:\]?)C(?P<col_abs>\[?)(?P<col_ref>[0-9\-]*)(?:\]?)$"
)
_RANGE = re.compile(r"^(?:\[([^\]]+)\])?(?:'?([^']+)'?!)?([a-zA-Z0-9:\-$\[\]]+)$")


class CellLimits:
    """The list R returns, with classes ``("cell_limits", "list")``."""

    def __init__(self, ul, lr, sheet=None):
        self.ul = list(ul)
        self.lr = list(lr)
        self.sheet = sheet
        self.classes = ("cell_limits", "list")

    def __str__(self) -> str:
        def piece(value):
            return "-" if value is None else str(int(value))

        sheet = "" if self.sheet is None else f" in '{self.sheet}'"
        return (
            f"<cell_limits ({piece(self.ul[0])}, {piece(self.ul[1])}) x "
            f"({piece(self.lr[0])}, {piece(self.lr[1])}){sheet}>"
        )

    def __repr__(self) -> str:
        return str(self)


def _missing(value) -> bool:
    return value is None


def _as_int(value, name: str):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    if value != int(value):
        raise ValueError(f"{name} must be a whole number")
    return int(value)


def cell_limits(ul=None, lr=None, sheet=None) -> CellLimits:
    """Upper-left and lower-right corners. ``None`` leaves that side open."""

    if ul is None:
        ul = [None, None]
    if lr is None:
        lr = [None, None]
    ul = list(ul)
    lr = list(lr)
    if len(ul) != 2 or len(lr) != 2:
        raise ValueError("ul and lr must have length 2")
    if sheet is not None and not isinstance(sheet, str):
        raise TypeError("sheet must be a string")
    parsed_ul = [None if item is None else _as_int(item, "ul") for item in ul]
    parsed_lr = [None if item is None else _as_int(item, "lr") for item in lr]
    for value in parsed_ul + parsed_lr:
        if value is not None and value <= 0:
            raise ValueError("row and column limits must be positive")
    if parsed_ul[0] is None and parsed_lr[0] is not None:
        parsed_ul[0] = 1
    if parsed_ul[1] is None and parsed_lr[1] is not None:
        parsed_ul[1] = 1
    if parsed_ul[0] is not None and parsed_lr[0] is not None and parsed_ul[0] > parsed_lr[0]:
        raise ValueError("the minimum row is greater than the maximum row")
    if parsed_ul[1] is not None and parsed_lr[1] is not None and parsed_ul[1] > parsed_lr[1]:
        raise ValueError("the minimum column is greater than the maximum column")
    return CellLimits(parsed_ul, parsed_lr, sheet)


def cell_rows(x) -> CellLimits:
    """Rows from the minimum to the maximum of ``x``. Columns stay open."""

    values = list(x) if isinstance(x, Sequence) and not isinstance(x, (str, bytes)) else [x]
    if all(item is None for item in values):
        return cell_limits()
    numbers = []
    for item in values:
        if item is None:
            numbers.append(None)
        else:
            numbers.append(_as_int(item, "x"))
    if len(numbers) != 2:
        present = [item for item in numbers if item is not None]
        if not present:
            return cell_limits()
        numbers = [min(present), max(present)]
    return cell_limits([numbers[0], None], [numbers[1], None])


def _letter_to_num(text: str):
    if text is None or text == "":
        return None
    total = 0
    for character in text.upper():
        if character < "A" or character > "Z":
            return None
        total = total * 26 + (ord(character) - ord("A") + 1)
    return total


def cell_cols(x) -> CellLimits:
    """Columns from the minimum to the maximum of ``x``. Rows stay open."""

    if isinstance(x, str):
        parts = x.split(":")
        numbers = [_letter_to_num(part) for part in parts]
    else:
        values = list(x) if isinstance(x, Sequence) and not isinstance(x, (str, bytes)) else [x]
        if values and isinstance(values[0], str):
            if len(values) == 1:
                values = values[0].split(":")
            numbers = [_letter_to_num(part) if part is not None else None for part in values]
        else:
            if all(item is None for item in values):
                return cell_limits()
            numbers = [None if item is None else _as_int(item, "x") for item in values]
    if all(item is None for item in numbers):
        return cell_limits()
    if len(numbers) != 2:
        present = [item for item in numbers if item is not None]
        numbers = [min(present), max(present)]
    return cell_limits([None, numbers[0]], [None, numbers[1]])


def _guess_format(text: str) -> str | None:
    r1c1 = _R1C1.match(text) is not None
    a1 = _A1.match(text) is not None
    if r1c1 and a1:
        return "R1C1"
    if r1c1:
        return "R1C1"
    if a1:
        return "A1"
    return None


def _parse_ref_string(text: str):
    matched = _RANGE.match(text)
    if matched is None:
        raise ValueError(f"Can't guess format of this cell reference:\n{text}")
    sheet = matched.group(2) or ""
    ref = matched.group(3)
    parts = ref.split(":")
    if len(parts) not in (1, 2):
        raise ValueError(f"Can't guess format of this cell reference:\n{text}")
    formats = [_guess_format(part) for part in parts]
    if any(item is None for item in formats) or len(set(formats)) != 1:
        raise ValueError(f"Can't guess format of this cell reference:\n{ref}")
    return {"sheet": sheet, "ref": ref, "parts": parts, "format": formats[0]}


def _a1_to_corner(text: str):
    matched = _A1_PARTS.search(text)
    if matched is None:
        raise ValueError(f"Can't guess format of this cell reference:\n{text}")
    row_abs = matched.group("row_abs") == "$"
    col_abs = matched.group("col_abs") == "$"
    if not row_abs and not col_abs:
        row_abs = True
        col_abs = True
    row = int(matched.group("row_ref")) if row_abs else None
    col = _letter_to_num(matched.group("col_ref")) if col_abs else None
    return row, col, row_abs and col_abs


def _r1c1_to_corner(text: str):
    matched = _R1C1_PARTS.match(text)
    if matched is None:
        raise ValueError(f"Can't guess format of this cell reference:\n{text}")
    row_abs_mark = matched.group("row_abs")
    col_abs_mark = matched.group("col_abs")
    row_ref = matched.group("row_ref")
    col_ref = matched.group("col_ref")
    if row_ref == "":
        row_abs_mark = "["
        row_ref = "0"
    if col_ref == "":
        col_abs_mark = "["
        col_ref = "0"
    row_abs = row_abs_mark == ""
    col_abs = col_abs_mark == ""
    row = int(row_ref) if row_abs else None
    col = int(col_ref) if col_abs else None
    return row, col, row_abs and col_abs


def as_cell_limits(x):
    """Turn ``None``, a :class:`CellLimits`, or a range string into corners."""

    if x is None:
        return cell_limits()
    if isinstance(x, CellLimits):
        return x
    if not isinstance(x, str):
        raise TypeError("range must be a string or a cell_limits object")
    parsed = _parse_ref_string(x)
    corners = []
    for part in parsed["parts"]:
        if parsed["format"] == "A1":
            row, col, absolute = _a1_to_corner(part)
        else:
            row, col, absolute = _r1c1_to_corner(part)
        if not absolute:
            raise ValueError(f"Mixed or relative cell references aren't allowed:\n{parsed['ref']}")
        corners.append((row, col))
    if len(corners) == 1:
        corners.append(corners[0])
    sheet = None if parsed["sheet"] == "" else parsed["sheet"]
    return cell_limits(
        [corners[0][0], corners[0][1]],
        [corners[1][0], corners[1][1]],
        sheet,
    )


def _extent(input, col_names, byrow):
    if input is None:
        raise TypeError("input is missing")
    shape = getattr(input, "shape", None)
    if shape is None or len(shape) == 1:
        length = len(input)
        extent = [1, length] if byrow else [length, 1]
        return extent, False
    if len(shape) != 2:
        raise ValueError("input must have one or two dimensions")
    rows, cols = int(shape[0]), int(shape[1])
    if col_names is None:
        names = getattr(input, "names", None)
        if names is None and hasattr(input, "columns"):
            names = list(input.columns)
        col_names = names is not None
    if col_names:
        rows += 1
    return [rows, cols], col_names


def anchored(anchor="A1", dim=(1, 1), input=None, col_names=None, byrow=False) -> CellLimits:
    """A rectangle of the given size whose upper left is ``anchor``."""

    if col_names not in (None, True, False) or byrow not in (True, False):
        raise ValueError("col_names and byrow must be TRUE or FALSE")
    origin = as_cell_limits(anchor)
    if origin.ul != origin.lr or None in origin.ul:
        raise ValueError("anchor must be one cell")
    if input is None:
        if len(dim) != 2:
            raise ValueError("dim must have length 2")
        extent = [int(dim[0]), int(dim[1])]
        if col_names is None:
            col_names = False
        if col_names:
            extent[0] += 1
    else:
        extent, col_names = _extent(input, col_names, byrow)
    return cell_limits(
        origin.ul,
        [origin.lr[0] + extent[0] - 1, origin.lr[1] + extent[1] - 1],
        origin.sheet,
    )
