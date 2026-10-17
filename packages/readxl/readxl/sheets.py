"""Worksheet names."""

from readxl.format import check_format
from readxl.read import _check_file


def excel_sheets(path):
    """The names of the sheets in an xls or xlsx workbook."""

    path = _check_file(path)
    if check_format(path) == "xls":
        import readxls

        return list(readxls.sheets(path))
    from readxl import xlsx_engine

    return list(xlsx_engine.sheets(path))
