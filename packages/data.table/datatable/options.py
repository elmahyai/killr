"""Numeric rounding used by data.table's radix sort. The default is 0."""

from datatable._util import DataTableError

_ROUNDING = 0


def get_numeric_rounding():
    """The current numeric rounding level, 0, 1, or 2."""
    return _ROUNDING


def set_numeric_rounding(x):
    """Set the numeric rounding level. The value is restored by the caller in checks."""
    global _ROUNDING
    try:
        level = int(x)
    except (TypeError, ValueError):
        raise DataTableError("x must be 0, 1, or 2") from None
    if level not in (0, 1, 2):
        raise DataTableError("x must be 0, 1, or 2")
    _ROUNDING = level
    return None
