"""Python translation of the R package readxl."""

from readxl.cells import anchored, cell_cols, cell_limits, cell_rows
from readxl.example import readxl_example, readxl_progress
from readxl.format import excel_format, format_from_ext, format_from_signature
from readxl.read import read_excel, read_xls, read_xlsx
from readxl.sheets import excel_sheets

__all__ = [
    "anchored",
    "cell_cols",
    "cell_limits",
    "cell_rows",
    "excel_format",
    "excel_sheets",
    "format_from_ext",
    "format_from_signature",
    "read_excel",
    "read_xls",
    "read_xlsx",
    "readxl_example",
    "readxl_progress",
]
