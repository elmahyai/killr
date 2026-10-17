"""Vector shapes pillar asks vctrs for.

A Python list of ints, floats, bools, or strings is an atomic vector.
None is a missing value. A list of lists is not an R list; use List.
NULL in R is the object None only when passed as the missing object
``NULL``. A bare None is a missing atom, so ``type_sum(NULL)`` is the
function ``type_sum`` of the ``NULL`` sentinel.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


class NULLType:
    def __repr__(self) -> str:
        return "NULL"


NULL = NULLType()


class Matrix:
    """Column-major matrix. ``data`` is the flat column-major values."""

    def __init__(self, data: list[Any], nrow: int, ncol: int | None = None):
        if ncol is None:
            if nrow == 0:
                ncol = 0
            else:
                ncol = len(data) // nrow
        self.data = list(data)
        self.nrow = int(nrow)
        self.ncol = int(ncol)

    @property
    def dim(self) -> tuple[int, int]:
        return (self.nrow, self.ncol)


class DataFrame:
    def __init__(self, columns: dict[str, list[Any]]):
        self.columns = {name: list(values) for name, values in columns.items()}
        lengths = [len(values) for values in self.columns.values()]
        self.nrow = lengths[0] if lengths else 0
        self.ncol = len(self.columns)

    @property
    def dim(self) -> tuple[int, int]:
        return (self.nrow, self.ncol)


class Factor:
    def __init__(self, values: list[Any], *, ordered: bool = False):
        self.values = list(values)
        self.ordered = ordered


class Table:
    def __init__(self, dims: tuple[int, ...]):
        self.dims = tuple(int(item) for item in dims)

    @property
    def dim(self) -> tuple[int, ...]:
        return self.dims


class List:
    """An R list, as opposed to an atomic vector."""

    def __init__(self, items: list[Any]):
        self.items = list(items)


class Environment:
    pass


def _dim(value: Any) -> tuple[int, ...] | None:
    if isinstance(value, (Matrix, DataFrame, Table)):
        return value.dim
    if isinstance(value, list) and getattr(value, "dim", None):
        return tuple(value.dim)
    return None


def vec_size(value: Any) -> int:
    """vctrs size. A matrix or data frame uses its first dimension."""

    dims = _dim(value)
    if dims is not None:
        return dims[0] if dims else 0
    if value is NULL:
        return 0
    if isinstance(value, List):
        return len(value.items)
    if isinstance(value, Factor):
        return len(value.values)
    if isinstance(value, (date, datetime)) and not isinstance(value, type):
        return 1
    if isinstance(value, (str, bytes, bool, int, float)) or value is None:
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def vec_is(value: Any) -> bool:
    if value is NULL or isinstance(value, (Environment, type)):
        return False
    if callable(value):
        return False
    if isinstance(value, (Matrix, DataFrame, Table, List, Factor, date, datetime, bytes)):
        return True
    if isinstance(value, (str, bool, int, float, complex)) or value is None:
        return True
    if isinstance(value, (list, tuple)):
        return True
    return False


def _bare(value: Any) -> str:
    if isinstance(value, Matrix):
        return _bare(value.data)
    if isinstance(value, list):
        kinds = [_atom_kind(item) for item in value if item is not None]
        if not kinds:
            return "lgl"
        if all(kind == "lgl" for kind in kinds):
            return "lgl"
        if all(kind == "int" for kind in kinds):
            return "int"
        if all(kind in {"int", "dbl"} for kind in kinds):
            return "dbl"
        if all(kind == "chr" for kind in kinds):
            return "chr"
        if all(kind == "cpl" for kind in kinds):
            return "cpl"
        return "list"
    return _atom_kind(value)


def _atom_kind(value: Any) -> str:
    if isinstance(value, bool):
        return "lgl"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "dbl"
    if isinstance(value, str):
        return "chr"
    if isinstance(value, complex):
        return "cpl"
    if isinstance(value, bytes):
        return "raw"
    if isinstance(value, list):
        return "list"
    return "list"


def _shape(value: Any) -> str:
    dims = _dim(value)
    if dims is None:
        return ""
    if len(dims) == 1:
        return "[1d]"
    rest = ",".join(str(item) for item in dims[1:])
    return "[," + rest + "]"


def vec_ptype_abbr(value: Any, *, suffix_shape: bool = True) -> str:
    if value is NULL:
        base = "NULL"
    elif isinstance(value, DataFrame):
        base = "df"
    elif isinstance(value, Factor):
        base = "ord" if value.ordered else "fct"
    elif isinstance(value, datetime):
        base = "dttm"
    elif isinstance(value, date):
        base = "date"
    elif isinstance(value, Table):
        base = "table"
    elif isinstance(value, List):
        base = "list"
    elif isinstance(value, bytes):
        base = "raw"
    else:
        base = _bare(value)
    if suffix_shape:
        return base + _shape(value)
    return base
