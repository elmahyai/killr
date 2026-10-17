"""Read a worksheet into a tibble."""

from __future__ import annotations

import math
import os
from collections.abc import Sequence

from tibble import new_tibble

from readxl.cells import CellLimits, as_cell_limits
from readxl.format import check_format
from readxl.names import repair


_TYPES = ("skip", "guess", "logical", "numeric", "date", "text", "list")


def _check_file(path) -> str:
    if not isinstance(path, str):
        raise ValueError("`path` must be a string")
    if not os.path.exists(path):
        raise ValueError(f"`path` does not exist: '{path}'")
    return os.path.realpath(path)


def _bool(value, name: str) -> bool:
    if value is not True and value is not False:
        raise ValueError(f"`{name}` must be either TRUE or FALSE")
    return value


def _non_negative(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"`{name}` must be a positive integer")
    if not math.isfinite(float(value)) and name != "n_max":
        raise ValueError(f"`{name}` must be a positive integer")
    number = float(value)
    if name == "n_max" and math.isinf(number) and number > 0:
        return number
    if number < 0 or number != math.floor(number) or math.isnan(number):
        raise ValueError(f"`{name}` must be a positive integer")
    return number


def _standardise_sheet(sheet, range_sheet, sheet_names: list[str]) -> int:
    if range_sheet is not None:
        if sheet is not None:
            print(
                "Two values given for `sheet`. "
                f"Using the `sheet` found in `range`:\n{range_sheet}"
            )
        sheet = range_sheet
    if sheet is None:
        sheet = 1
    if isinstance(sheet, (list, tuple)):
        if len(sheet) != 1:
            raise ValueError("`sheet` must have length 1")
        sheet = sheet[0]
    if isinstance(sheet, bool) or isinstance(sheet, (int, float)) and not isinstance(sheet, bool):
        if isinstance(sheet, bool) or sheet < 1:
            if isinstance(sheet, bool) or not isinstance(sheet, (int, float)):
                raise ValueError("`sheet` must be either an integer or a string.")
            if sheet < 1:
                raise ValueError("`sheet` must be positive")
        return int(math.floor(sheet)) - 1
    if isinstance(sheet, str):
        if sheet not in sheet_names:
            raise ValueError(f"Sheet '{sheet}' not found")
        return sheet_names.index(sheet)
    raise ValueError("`sheet` must be either an integer or a string.")


def _standardise_limits(range_obj, skip, n_max, has_col_names: bool):
    if range_obj is None:
        skip = _non_negative(skip, "skip")
        n_max = _non_negative(n_max, "n_max")
        n_read = n_max + 1 if has_col_names else n_max
        if n_read > 0:
            min_row = int(skip)
        else:
            min_row = -2
        if math.isinf(n_read) or n_read == 0:
            max_row = -1
        else:
            max_row = int(skip + n_read - 1)
        return [min_row, max_row, -1, -1]
    limits = as_cell_limits(range_obj)

    def corner(value):
        return -1 if value is None else int(value) - 1

    return [corner(limits.ul[0]), corner(limits.lr[0]), corner(limits.ul[1]), corner(limits.lr[1])]


def _col_types(col_types):
    if col_types is None:
        return ["guess"]
    if isinstance(col_types, str):
        col_types = [col_types]
    if not col_types or any(item is None or not isinstance(item, str) for item in col_types):
        raise ValueError("col_types must be a character vector")
    out = []
    bad = []
    for index, item in enumerate(col_types):
        if item == "blank":
            print('`col_type = "blank"` deprecated. Use "skip" instead.')
            item = "skip"
        if item not in _TYPES:
            bad.append(f"'{item}' [{index + 1}]")
        out.append(item)
    if bad:
        raise ValueError("Illegal column type: " + ", ".join(bad))
    return out


def _frame(result, name_repair):
    names = list(result["names"])
    columns = list(result["columns"])
    if callable(name_repair):
        names = list(name_repair(names))
    elif name_repair is not None:
        names = repair(names, name_repair)
    if not columns:
        return new_tibble([], nrow=0, names=[])
    return new_tibble(columns, names=names)


def _read(path, sheet, range, col_names, col_types, na, trim_ws, skip, n_max, guess_max, name_repair, format):
    path = _check_file(path)
    trim_ws = _bool(trim_ws, "trim_ws")
    if isinstance(na, str):
        na = [na]
    na = ["" if item is None else str(item) for item in na]
    types = _col_types(col_types)
    guess_max = _non_negative(guess_max, "guess_max")
    limit = 2147483647 // 100
    if guess_max > limit:
        import warnings

        warnings.warn(
            f"`guess_max` is a very large value, setting to `{limit}` to avoid exhausting memory",
            UserWarning,
            stacklevel=3,
        )
        guess_max = limit
    if format == "xls":
        import readxls as engine

        sheet_names = engine.sheets(path)
    else:
        from readxl import xlsx_engine as engine

        sheet_names = engine.sheets(path)
    range_sheet = None
    if range is not None:
        parsed = range if isinstance(range, CellLimits) else as_cell_limits(range)
        range_sheet = parsed.sheet
    sheet_i = _standardise_sheet(sheet, range_sheet, list(sheet_names))
    has_col_names = col_names is True
    limits = _standardise_limits(range, skip, n_max, has_col_names)
    shim = range is not None
    result = engine.read(
        path,
        int(sheet_i),
        [int(item) for item in limits],
        shim,
        col_names,
        types,
        na,
        trim_ws,
        int(guess_max),
    )
    return _frame(result, name_repair)


def read_excel(
    path,
    sheet=None,
    range=None,
    col_names=True,
    col_types=None,
    na="",
    trim_ws=True,
    skip=0,
    n_max=math.inf,
    guess_max=None,
    progress=None,
    name_repair="unique",
):
    """Read one sheet of an xls or xlsx workbook."""

    path = _check_file(path)
    if guess_max is None:
        guess_max = min(1000, n_max) if not isinstance(n_max, bool) else 1000
    if progress is not None:
        _bool(progress, "progress")
    return _read(
        path,
        sheet,
        range,
        col_names,
        col_types,
        na,
        trim_ws,
        skip,
        n_max,
        guess_max,
        name_repair,
        check_format(path),
    )


def read_xls(
    path,
    sheet=None,
    range=None,
    col_names=True,
    col_types=None,
    na="",
    trim_ws=True,
    skip=0,
    n_max=math.inf,
    guess_max=None,
    progress=None,
    name_repair="unique",
):
    """Read one sheet of an xls workbook."""

    if guess_max is None:
        guess_max = min(1000, n_max)
    if progress is not None:
        _bool(progress, "progress")
    return _read(
        path, sheet, range, col_names, col_types, na, trim_ws, skip, n_max, guess_max, name_repair, "xls"
    )


def read_xlsx(
    path,
    sheet=None,
    range=None,
    col_names=True,
    col_types=None,
    na="",
    trim_ws=True,
    skip=0,
    n_max=math.inf,
    guess_max=None,
    progress=None,
    name_repair="unique",
):
    """Read one sheet of an xlsx workbook."""

    if guess_max is None:
        guess_max = min(1000, n_max)
    if progress is not None:
        _bool(progress, "progress")
    return _read(
        path, sheet, range, col_names, col_types, na, trim_ws, skip, n_max, guess_max, name_repair, "xlsx"
    )
