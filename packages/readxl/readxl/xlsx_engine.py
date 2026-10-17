"""xlsx reader.

``sheets(path)`` returns sheet names in workbook order.

``read(path, sheet_i, limits, shim, col_names, col_types, na, trim_ws, guess_max)``
returns ``{"names": [...], "columns": [...]}``. ``sheet_i`` is 0-based.
``limits`` is ``[min_row, max_row, min_col, max_col]``, 0-based, with -1 for
an open side and -2 for a minimum row that means read nothing. ``shim`` is
true when the caller passed a range. Follow ``src/Read.cpp``, ``SheetView.h``,
``ColSpec.h``, ``utils.h``, ``XlsxWorkBook.h``, ``XlsxCell.h``, and
``XlsxCellSet.h``. Missing values are ``None``. Dates are POSIX seconds in
UTC, the same numbers as readxl's POSIXct column.
"""


def sheets(path: str) -> list[str]:
    raise NotImplementedError("xlsx sheets are not ported")


def read(path, sheet_i, limits, shim, col_names, col_types, na, trim_ws, guess_max):
    raise NotImplementedError("xlsx reading is not ported")
