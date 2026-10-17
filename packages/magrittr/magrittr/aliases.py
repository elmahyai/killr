"""Aliases of the R operators magrittr exports for pipes.

Indexing is 1-based. ``and_``, ``or_``, and ``not_`` are elementwise, matching
R's ``&``, ``|``, and ``!``. A matrix built from a flat vector is filled down
columns, which is how R stores a matrix.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np


class NAType:
    """R's missing value. Equality with it is missing, not true or false."""

    def __repr__(self) -> str:
        return "NA"

    def __bool__(self) -> bool:
        raise ValueError("missing value where TRUE/FALSE needed")


NA = NAType()


class Vector:
    """Atomic vector. ``names`` lines up with ``values`` when it is present."""

    def __init__(
        self,
        values: Any,
        names: Any = None,
        attributes: dict[str, Any] | None = None,
        r_class: Any = None,
    ) -> None:
        self.values = list(values)
        self.names = _fit_names(names, len(self.values), strict=True)
        self.attributes = {} if attributes is None else dict(attributes)
        self.r_class = _class_list(r_class)

    def copy(self) -> Vector:
        return Vector(
            self.values,
            None if self.names is None else list(self.names),
            dict(self.attributes),
            None if self.r_class is None else list(self.r_class),
        )

    def pairs(self) -> list[tuple[Any, Any]]:
        names = self.names if self.names is not None else [None] * len(self.values)
        return list(zip(names, self.values))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector):
            return NotImplemented
        return (
            self.values == other.values
            and self.names == other.names
            and self.attributes == other.attributes
            and self.r_class == other.r_class
        )

    def __repr__(self) -> str:
        return (
            f"Vector(values={self.values!r}, names={self.names!r}, "
            f"attributes={self.attributes!r}, r_class={self.r_class!r})"
        )


class RList:
    """R list. Elements keep their order, and names line up with them."""

    def __init__(self, values: Any, names: Any = None) -> None:
        self.values = list(values)
        if names is None:
            self.names = None
        else:
            got = list(names)
            if len(got) != len(self.values):
                raise ValueError("names must have one entry per element")
            self.names = [None if name is None else str(name) for name in got]

    def copy(self) -> RList:
        return RList(list(self.values), None if self.names is None else list(self.names))

    def pairs(self) -> list[tuple[Any, Any]]:
        names = self.names if self.names is not None else [None] * len(self.values)
        return list(zip(names, self.values))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RList):
            return NotImplemented
        return self.values == other.values and self.names == other.names

    def __repr__(self) -> str:
        return f"RList(values={self.values!r}, names={self.names!r})"


class Matrix:
    """Numeric matrix in row-and-column layout.

    ``data`` is a flat sequence in column-major order, the order R uses when
    it builds ``matrix(data, nrow)``. ``cells()`` returns rows, so a product
    is compared by those cells.
    """

    def __init__(
        self,
        data: Any,
        nrow: int,
        ncol: int | None = None,
        rownames: Any = None,
        colnames: Any = None,
    ) -> None:
        if isinstance(data, np.ndarray) and data.ndim == 2 and ncol is None:
            array = np.array(data, copy=True)
        else:
            flat = [_plain(value) for value in list(data)]
            if nrow < 0:
                raise ValueError("invalid 'nrow' value")
            if ncol is None:
                if nrow == 0 or len(flat) % nrow != 0:
                    raise ValueError("data length is not a multiple of nrow")
                ncol = len(flat) // nrow
            if len(flat) != nrow * ncol:
                raise ValueError("data length does not match nrow * ncol")
            array = np.array(flat).reshape((nrow, ncol), order="F")
        self.data = array
        self.rownames = _dimnames(rownames, self.data.shape[0], "row")
        self.colnames = _dimnames(colnames, self.data.shape[1], "col")

    def copy(self) -> Matrix:
        out = Matrix.__new__(Matrix)
        out.data = self.data.copy()
        out.rownames = None if self.rownames is None else list(self.rownames)
        out.colnames = None if self.colnames is None else list(self.colnames)
        return out

    def cells(self) -> list[list[Any]]:
        rows = []
        for i in range(self.data.shape[0]):
            row = []
            for j in range(self.data.shape[1]):
                row.append(_plain(self.data[i, j]))
            rows.append(row)
        return rows

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Matrix):
            return NotImplemented
        return (
            self.data.shape == other.data.shape
            and np.array_equal(self.data, other.data)
            and self.rownames == other.rownames
            and self.colnames == other.colnames
        )

    def __repr__(self) -> str:
        return (
            f"Matrix(cells={self.cells()!r}, rownames={self.rownames!r}, "
            f"colnames={self.colnames!r})"
        )


def _plain(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return value


def _is_na(value: Any) -> bool:
    if value is NA or value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _is_scalar(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float, str, NAType)):
        return True
    if isinstance(value, np.generic):
        return True
    return False


def _class_list(r_class: Any) -> list[str] | None:
    if r_class is None:
        return None
    if isinstance(r_class, str):
        return [r_class]
    return [str(item) for item in r_class]


def _fit_names(names: Any, n: int, strict: bool) -> list[Any] | None:
    if names is None:
        return None
    if isinstance(names, str):
        got = [names]
    else:
        got = list(names)
    if len(got) > n:
        raise ValueError(
            f"'names' attribute [{len(got)}] must be the same length as the vector [{n}]"
        )
    if len(got) < n:
        if strict and len(got) != n:
            raise ValueError(
                f"'names' attribute [{len(got)}] must be the same length as the vector [{n}]"
            )
        got = got + [None] * (n - len(got))
    return [None if name is None else str(name) for name in got]


def _dimnames(names: Any, n: int, axis: str) -> list[str] | None:
    if names is None:
        return None
    got = [names] if isinstance(names, str) else list(names)
    if len(got) != n:
        raise ValueError(f"length of 'dimnames' [{len(got)}] not equal to array extent")
    return [str(name) for name in got]


def _values_and_names(value: Any) -> tuple[list[Any], list[Any] | None]:
    if isinstance(value, Vector):
        return list(value.values), None if value.names is None else list(value.names)
    if isinstance(value, RList):
        return list(value.values), None if value.names is None else list(value.names)
    if isinstance(value, dict):
        return list(value.values()), [str(key) for key in value.keys()]
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return [_plain(value)], None
        if value.ndim != 1:
            raise TypeError("a matrix belongs in multiply_by_matrix, set_colnames, or set_rownames")
        return [_plain(item) for item in value.tolist()], None
    if isinstance(value, (list, tuple)):
        return list(value), None
    if _is_scalar(value):
        return [_plain(value)], None
    raise TypeError(f"cannot use {type(value).__name__} as a vector")


def _result_names(
    n1: int,
    names1: list[Any] | None,
    n2: int,
    names2: list[Any] | None,
    nout: int,
) -> list[Any] | None:
    """Names come from the longer side, and from the left when lengths match."""

    if n1 == n2:
        if names1 is not None:
            return list(names1)
        if names2 is not None:
            return list(names2)
        return None
    if n1 == nout and names1 is not None:
        return list(names1)
    if n2 == nout and names2 is not None:
        return list(names2)
    return None


def _recycle(values: list[Any], n: int) -> list[Any]:
    if len(values) == n:
        return list(values)
    if len(values) == 0:
        return []
    return [values[i % len(values)] for i in range(n)]


def _box(values: list[Any], names: list[Any] | None, scalar: bool) -> Any:
    cleaned = [_plain(value) for value in values]
    if names is not None:
        return Vector(cleaned, names)
    if scalar and len(cleaned) == 1:
        return cleaned[0]
    return cleaned


def _binary(e1: Any, e2: Any, fn: Any) -> Any:
    scalar = _is_scalar(e1) and _is_scalar(e2)
    v1, n1 = _values_and_names(e1)
    v2, n2 = _values_and_names(e2)
    if len(v1) == 0 or len(v2) == 0:
        return _box([], None, False)
    nout = max(len(v1), len(v2))
    shorter = min(len(v1), len(v2))
    if shorter and nout % shorter != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            stacklevel=3,
        )
    left = _recycle(v1, nout)
    right = _recycle(v2, nout)
    values = [fn(a, b) for a, b in zip(left, right)]
    names = _result_names(len(v1), n1, len(v2), n2, nout)
    if names is not None and len(names) != nout:
        names = None
    return _box(values, names, scalar)


def _as_logical(value: Any) -> bool | None:
    if _is_na(value):
        return None
    if isinstance(value, str):
        raise TypeError("cannot coerce a string to logical")
    return bool(value != 0) if not isinstance(value, bool) else value


def _and(a: Any, b: Any) -> bool | None:
    left, right = _as_logical(a), _as_logical(b)
    if left is False or right is False:
        return False
    if left is None or right is None:
        return None
    return True


def _or(a: Any, b: Any) -> bool | None:
    left, right = _as_logical(a), _as_logical(b)
    if left is True or right is True:
        return True
    if left is None or right is None:
        return None
    return False


def _compare(a: Any, b: Any, fn: Any) -> bool | None:
    if _is_na(a) or _is_na(b):
        return None
    return bool(fn(a, b))


def _floor_div(a: Any, b: Any) -> Any:
    """R ``%/%``. ``-7 %/% 2`` is ``-4``."""

    if _is_na(a) or _is_na(b):
        return float("nan")
    if b == 0:
        if a == 0:
            return float("nan")
        return float("inf") if a > 0 else float("-inf")
    return a // b


def _mod(a: Any, b: Any) -> Any:
    """R ``%%``. The remainder takes the sign of the divisor."""

    if _is_na(a) or _is_na(b) or b == 0:
        return float("nan")
    return a - b * (a // b)


def _power(a: Any, b: Any) -> Any:
    if _is_na(a) or _is_na(b):
        return float("nan")
    try:
        result = a ** b
    except ZeroDivisionError:
        return float("inf")
    if isinstance(result, complex):
        return float("nan")
    return result


def _unary(x: Any, fn: Any) -> Any:
    scalar = _is_scalar(x)
    values, names = _values_and_names(x)
    return _box([fn(value) for value in values], names, scalar)


def add(e1: Any, e2: Any) -> Any:
    """Elementwise sum, the alias of ``+``."""

    return _binary(e1, e2, lambda a, b: float("nan") if _is_na(a) or _is_na(b) else a + b)


def subtract(e1: Any, e2: Any = None) -> Any:
    """Elementwise difference, the alias of ``-``.

    With one argument this is unary minus.
    """

    if e2 is None:
        return _unary(e1, lambda a: float("nan") if _is_na(a) else -a)
    return _binary(e1, e2, lambda a, b: float("nan") if _is_na(a) or _is_na(b) else a - b)


def multiply_by(e1: Any, e2: Any) -> Any:
    """Elementwise product, the alias of ``*``."""

    return _binary(e1, e2, lambda a, b: float("nan") if _is_na(a) or _is_na(b) else a * b)


def divide_by(e1: Any, e2: Any) -> Any:
    """Elementwise ratio, the alias of ``/``. The result is floating point."""

    def _div(a: Any, b: Any) -> Any:
        if _is_na(a) or _is_na(b):
            return float("nan")
        if b == 0:
            if a == 0:
                return float("nan")
            return float("inf") if a > 0 else float("-inf")
        return a / b

    return _binary(e1, e2, _div)


def divide_by_int(e1: Any, e2: Any) -> Any:
    """Elementwise integer division, the alias of ``%/%``.

    Division floors toward negative infinity, so ``divide_by_int(-7, 2)`` is ``-4``.
    """

    return _binary(e1, e2, _floor_div)


def raise_to_power(e1: Any, e2: Any) -> Any:
    """Elementwise power, the alias of ``^``."""

    return _binary(e1, e2, _power)


def mod(e1: Any, e2: Any) -> Any:
    """Elementwise remainder, the alias of ``%%``.

    The remainder takes the sign of the divisor, as in R.
    """

    return _binary(e1, e2, _mod)


def _as_matrix(value: Any) -> tuple[np.ndarray, str]:
    if isinstance(value, Matrix):
        return np.asarray(value.data, dtype=float), "matrix"
    if isinstance(value, np.ndarray) and value.ndim == 2:
        return np.asarray(value, dtype=float), "matrix"
    values, _names = _values_and_names(value)
    return np.asarray(values, dtype=float), "vector"


def multiply_by_matrix(x: Any, y: Any) -> Matrix:
    """Matrix product, the alias of ``%*%``.

    A :class:`Matrix` is filled down columns. A vector on the left becomes a
    row when its length is the number of rows on the right. A vector on the
    right becomes a column when its length is the number of columns on the
    left. Two vectors of equal length return their inner product as a 1 by 1
    matrix.
    """

    left, left_kind = _as_matrix(x)
    right, right_kind = _as_matrix(y)
    if left_kind == "vector" and right_kind == "vector":
        if left.shape[0] != right.shape[0]:
            raise ValueError("non-conformable arguments")
        result = np.array([[float(np.dot(left, right))]])
    elif left_kind == "vector" and right_kind == "matrix":
        if left.shape[0] != right.shape[0]:
            raise ValueError("non-conformable arguments")
        result = left.reshape(1, -1) @ right
    elif left_kind == "matrix" and right_kind == "vector":
        if right.shape[0] != left.shape[1]:
            raise ValueError("non-conformable arguments")
        result = left @ right.reshape(-1, 1)
    else:
        if left.shape[1] != right.shape[0]:
            raise ValueError("non-conformable arguments")
        result = left @ right
    out = Matrix.__new__(Matrix)
    out.data = np.asarray(result, dtype=float)
    out.rownames = None
    out.colnames = None
    return out


def is_in(x: Any, table: Any) -> Any:
    """Elementwise membership, the alias of ``%in%``.

    The test runs once for each value on the left. A missing value matches a
    missing value in ``table``.
    """

    values, names = _values_and_names(x)
    pool, _pool_names = _values_and_names(table)
    pool_has_na = any(_is_na(item) for item in pool)
    out: list[bool] = []
    for item in values:
        if _is_na(item):
            out.append(pool_has_na)
            continue
        out.append(any(item == other for other in pool if not _is_na(other)))
    return _box(out, names, _is_scalar(x))


def and_(e1: Any, e2: Any) -> Any:
    """Elementwise conjunction, the alias of ``&``.

    Both sides are evaluated. This is not Python's short-circuit ``and``.
    ``FALSE`` wins over a missing value.
    """

    return _binary(e1, e2, _and)


def or_(e1: Any, e2: Any) -> Any:
    """Elementwise disjunction, the alias of ``|``.

    Both sides are evaluated. This is not Python's short-circuit ``or``.
    ``TRUE`` wins over a missing value.
    """

    return _binary(e1, e2, _or)


def equals(e1: Any, e2: Any) -> Any:
    """Elementwise equality, the alias of ``==``. A missing value compares as missing."""

    return _binary(e1, e2, lambda a, b: _compare(a, b, lambda u, v: u == v))


def is_greater_than(e1: Any, e2: Any) -> Any:
    """Elementwise ``>``."""

    return _binary(e1, e2, lambda a, b: _compare(a, b, lambda u, v: u > v))


def is_weakly_greater_than(e1: Any, e2: Any) -> Any:
    """Elementwise ``>=``."""

    return _binary(e1, e2, lambda a, b: _compare(a, b, lambda u, v: u >= v))


def is_less_than(e1: Any, e2: Any) -> Any:
    """Elementwise ``<``."""

    return _binary(e1, e2, lambda a, b: _compare(a, b, lambda u, v: u < v))


def is_weakly_less_than(e1: Any, e2: Any) -> Any:
    """Elementwise ``<=``."""

    return _binary(e1, e2, lambda a, b: _compare(a, b, lambda u, v: u <= v))


def not_(x: Any) -> Any:
    """Elementwise negation, the alias of ``!``.

    Zero is false and any other number is true. A missing value stays missing.
    """

    def _negate(value: Any) -> bool | None:
        logical = _as_logical(value)
        if logical is None:
            return None
        return not logical

    return _unary(x, _negate)


nest_pas = not_


def _normalize_index(index: Any) -> tuple[str, list[Any] | None]:
    if index is None:
        return "missing", None
    if isinstance(index, bool):
        return "logical", [index]
    if isinstance(index, (int, np.integer)) and not isinstance(index, bool):
        return "integer", [int(index)]
    if isinstance(index, float):
        if math.isnan(index):
            return "integer", [None]
        return "integer", [int(index)]
    if isinstance(index, str):
        return "character", [index]
    if isinstance(index, Vector):
        return _normalize_index(index.values)
    if isinstance(index, np.ndarray) and index.ndim == 1:
        return _normalize_index(index.tolist())
    if isinstance(index, (list, tuple)):
        if len(index) == 0:
            return "integer", []
        if all(isinstance(item, bool) for item in index):
            return "logical", [bool(item) for item in index]
        if all(isinstance(item, str) or item is None for item in index):
            return "character", list(index)
        ints: list[int | None] = []
        for item in index:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                ints.append(None)
            elif isinstance(item, bool):
                raise ValueError("only 0's may be mixed with negative subscripts")
            elif isinstance(item, float):
                ints.append(int(item))
            else:
                ints.append(int(item))
        return "integer", ints
    raise TypeError("invalid subscript type")


def _positions(n: int, index: Any, names: list[Any] | None) -> list[int | None]:
    kind, spec = _normalize_index(index)
    if kind == "missing":
        return list(range(n))
    assert spec is not None
    if kind == "character":
        if names is None:
            return [None] * len(spec)
        out: list[int | None] = []
        for name in spec:
            hits = [i for i, got in enumerate(names) if got == name]
            out.append(hits[0] if hits else None)
        return out
    if kind == "logical":
        flags = list(spec)
        if len(flags) == 0:
            return []
        if len(flags) < n and n % len(flags) != 0:
            warnings.warn(
                "longer object length is not a multiple of shorter object length",
                stacklevel=4,
            )
        if len(flags) <= n:
            flags = _recycle(flags, n)
            return [i for i, flag in enumerate(flags) if flag]
        chosen: list[int | None] = []
        for i, flag in enumerate(flags):
            if flag:
                chosen.append(i if i < n else None)
        return chosen
    ints = list(spec)
    if any(item is not None and item < 0 for item in ints) and any(
        item is not None and item > 0 for item in ints
    ):
        raise ValueError("only 0's may be mixed with negative subscripts")
    if any(item is not None and item < 0 for item in ints):
        drop = {abs(item) for item in ints if item is not None and item < 0}
        return [i for i in range(n) if (i + 1) not in drop]
    chosen = []
    for item in ints:
        if item is None:
            chosen.append(None)
        elif item == 0:
            continue
        elif item < 1 or item > n:
            chosen.append(None)
        else:
            chosen.append(item - 1)
    return chosen


def _take(x: Any, positions: list[int | None]) -> Any:
    values, names = _values_and_names(x)
    numeric = any(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values)
    picked: list[Any] = []
    picked_names: list[Any] = []
    for pos in positions:
        if pos is None:
            picked.append(float("nan") if numeric else NA)
            picked_names.append(None)
        else:
            picked.append(values[pos])
            if names is not None:
                picked_names.append(names[pos])
    out_names = picked_names if names is not None else None
    if isinstance(x, RList):
        return RList(picked, out_names)
    if isinstance(x, dict):
        if out_names is None:
            return picked
        return dict(zip(["" if name is None else name for name in out_names], picked))
    if isinstance(x, Vector) or out_names is not None:
        attributes = dict(x.attributes) if isinstance(x, Vector) else None
        r_class = list(x.r_class) if isinstance(x, Vector) and x.r_class is not None else None
        return Vector(picked, out_names, attributes, r_class)
    return picked


def _dim_positions(n: int, index: Any) -> list[int]:
    positions = _positions(n, index, None)
    if any(pos is None for pos in positions):
        raise IndexError("subscript out of bounds")
    return [pos for pos in positions if pos is not None]


def _subset_matrix(matrix: Matrix, index: tuple[Any, ...], drop: bool) -> Any:
    if len(index) == 1:
        flat = matrix.data.ravel(order="F")
        positions = _positions(flat.size, index[0], None)
        values: list[Any] = []
        for pos in positions:
            if pos is None:
                values.append(float("nan"))
            else:
                values.append(_plain(flat[pos]))
        if drop and len(values) == 1:
            return values[0]
        return values
    if len(index) != 2:
        raise ValueError("incorrect number of dimensions")
    rows = list(range(matrix.data.shape[0])) if index[0] is None else _dim_positions(matrix.data.shape[0], index[0])
    cols = list(range(matrix.data.shape[1])) if index[1] is None else _dim_positions(matrix.data.shape[1], index[1])
    data = matrix.data[np.ix_(rows, cols)]
    rownames = None if matrix.rownames is None else [matrix.rownames[i] for i in rows]
    colnames = None if matrix.colnames is None else [matrix.colnames[j] for j in cols]
    if drop and data.shape[0] == 1 and data.shape[1] == 1:
        return _plain(data[0, 0])
    if drop and data.shape[0] == 1:
        names = colnames
        return Vector([_plain(value) for value in data[0, :].tolist()], names) if names else [
            _plain(value) for value in data[0, :].tolist()
        ]
    if drop and data.shape[1] == 1:
        names = rownames
        column = [_plain(value) for value in data[:, 0].tolist()]
        return Vector(column, names) if names else column
    out = Matrix.__new__(Matrix)
    out.data = data.copy()
    out.rownames = rownames
    out.colnames = colnames
    return out


def extract(x: Any, *index: Any, drop: bool = True) -> Any:
    """One-based ``[``.

    A positive index selects, zero is ignored, and a negative index drops.
    Names follow the selected elements. On a matrix, one index walks down
    columns, and two indexes select rows and columns.
    """

    if isinstance(x, Matrix):
        if not index:
            return x.copy()
        return _subset_matrix(x, index, drop)
    if not index:
        return _take(x, list(range(len(_values_and_names(x)[0]))))
    if len(index) != 1:
        raise ValueError("incorrect number of dimensions")
    values, names = _values_and_names(x)
    return _take(x, _positions(len(values), index[0], names))


def _lookup(names: list[Any] | None, name: str, partial: bool) -> int | None:
    if names is None:
        return None
    exact = [i for i, got in enumerate(names) if got == name]
    if exact:
        return exact[0]
    if not partial or name == "":
        return None
    hits = [i for i, got in enumerate(names) if isinstance(got, str) and got.startswith(name)]
    if len(hits) == 1:
        warnings.warn(f"partial match of '{name}' to '{names[hits[0]]}'", stacklevel=3)
        return hits[0]
    if len(hits) > 1:
        warnings.warn(f"partial match of '{name}' has multiple matches", stacklevel=3)
        return None
    return None


def _element(x: Any, pos: int) -> Any:
    if isinstance(x, (Vector, RList)):
        return x.values[pos]
    if isinstance(x, dict):
        return list(x.values())[pos]
    return list(x)[pos]


def describe(value: Any) -> dict[str, Any]:
    """JSON-ready view of a result: names stay in order beside their values."""

    blank: dict[str, Any] = {
        "names": None,
        "values": None,
        "cells": None,
        "rownames": None,
        "colnames": None,
        "class": None,
        "attr": None,
    }
    if isinstance(value, Matrix):
        blank["cells"] = value.cells()
        blank["rownames"] = value.rownames
        blank["colnames"] = value.colnames
        return blank
    if isinstance(value, Vector):
        blank["names"] = value.names
        blank["values"] = value.values
        blank["class"] = value.r_class
        blank["attr"] = value.attributes or None
        return blank
    if isinstance(value, RList):
        blank["names"] = value.names
        blank["values"] = value.values
        return blank
    if isinstance(value, list):
        blank["values"] = value
        return blank
    blank["values"] = [value]
    return blank


def extract2(x: Any, index: Any, exact: bool = True) -> Any:
    """One-based ``[[``. One index, and the element is returned unwrapped.

    A character index matches the whole name when ``exact`` is true.
    """

    if isinstance(index, str):
        names = _values_and_names(x)[1]
        found = _lookup(names, index, partial=not exact)
        if found is None:
            return None
        return _element(x, found)
    kind, spec = _normalize_index(index)
    if kind != "integer" or spec is None or len(spec) != 1 or spec[0] is None or spec[0] < 1:
        raise IndexError("attempt to select less than one element" if spec and spec[0] == 0 else "subscript out of bounds")
    pos = spec[0]
    n = len(_values_and_names(x)[0])
    if pos > n:
        raise IndexError("subscript out of bounds")
    return _element(x, pos - 1)


def use_series(x: Any, name: str) -> Any:
    """``$``. ``name`` is a string. An exact name wins, otherwise a unique prefix."""

    if not isinstance(name, str):
        raise TypeError("use_series expects the element name as a string")
    names = _values_and_names(x)[1]
    found = _lookup(names, name, partial=True)
    if found is None:
        return None
    return _element(x, found)


def _replacement_values(value: Any, n: int) -> list[Any]:
    values, _names = _values_and_names(value)
    if n == 0:
        return []
    if len(values) == 0:
        raise ValueError("replacement has length zero")
    if n % len(values) != 0:
        warnings.warn(
            "number of items to replace is not a multiple of replacement length",
            stacklevel=4,
        )
    return _recycle(values, n)


def _inset_atomic(x: Any, index: Any, value: Any) -> Any:
    values, names = _values_and_names(x)
    kind, spec = _normalize_index(index)
    if kind == "missing":
        positions = list(range(len(values)))
        extend = 0
    elif kind == "character":
        assert spec is not None
        positions = []
        extra_names: list[Any] = []
        current = [] if names is None else list(names)
        for name in spec:
            hits = [i for i, got in enumerate(current) if got == name]
            if hits:
                positions.append(hits[0])
            else:
                positions.append(len(values) + len(extra_names))
                extra_names.append(name)
        if extra_names:
            values = values + [_missing_value(values) for _ in extra_names]
            if current:
                names = current + extra_names
            else:
                names = [None] * (len(values) - len(extra_names)) + extra_names
        extend = 0
    else:
        assert spec is not None
        if kind == "logical":
            positions = [pos for pos in _positions(len(values), index, names) if pos is not None]
            extend = 0
        else:
            if any(item is not None and item < 0 for item in spec):
                raise ValueError("negative subscripts are not allowed in subscripted assignments")
            positions = []
            extend = len(values)
            for item in spec:
                if item is None:
                    raise ValueError("NAs are not allowed in subscripted assignments")
                if item == 0:
                    continue
                positions.append(item - 1)
                if item > extend:
                    extend = item
            if extend > len(values):
                values = values + [_missing_value(values) for _ in range(extend - len(values))]
                if names is not None:
                    names = list(names) + [None] * (extend - len(names))
    replacing = _replacement_values(value, len(positions))
    for pos, item in zip(positions, replacing):
        values[pos] = item
    if isinstance(x, RList):
        return RList(values, names)
    if isinstance(x, Vector) or names is not None:
        attributes = dict(x.attributes) if isinstance(x, Vector) else None
        r_class = list(x.r_class) if isinstance(x, Vector) and x.r_class is not None else None
        return Vector(values, names, attributes, r_class)
    return values


def _missing_value(values: list[Any]) -> Any:
    if any(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
        return float("nan")
    if any(isinstance(value, str) for value in values):
        return NA
    return None


def _inset_matrix(matrix: Matrix, index: tuple[Any, ...], value: Any) -> Matrix:
    out = matrix.copy()
    if len(index) == 1:
        flat = out.data.ravel(order="F").copy()
        positions = [pos for pos in _positions(flat.size, index[0], None) if pos is not None]
        replacing = _replacement_values(value, len(positions))
        for pos, item in zip(positions, replacing):
            flat[pos] = item
        out.data = flat.reshape(out.data.shape, order="F")
        return out
    if len(index) != 2:
        raise ValueError("incorrect number of dimensions")
    rows = list(range(out.data.shape[0])) if index[0] is None else _dim_positions(out.data.shape[0], index[0])
    cols = list(range(out.data.shape[1])) if index[1] is None else _dim_positions(out.data.shape[1], index[1])
    slots = [(i, j) for i in rows for j in cols]
    replacing = _replacement_values(value, len(slots))
    for (i, j), item in zip(slots, replacing):
        out.data[i, j] = item
    return out


def inset(x: Any, *args: Any) -> Any:
    """``[<-``. The last argument is the replacement. Indexes are 1-based.

    The input is not modified. The returned object carries the replacement.
    """

    if not args:
        raise TypeError("inset requires a replacement value")
    *index, value = args
    if isinstance(x, Matrix):
        if not index:
            raise ValueError("incorrect number of dimensions")
        return _inset_matrix(x, tuple(index), value)
    if len(index) != 1:
        raise ValueError("incorrect number of dimensions")
    return _inset_atomic(x, index[0], value)


def _restore(x: Any, values: list[Any], names: list[Any] | None) -> Any:
    if isinstance(x, Vector):
        return Vector(
            values,
            names,
            dict(x.attributes),
            None if x.r_class is None else list(x.r_class),
        )
    if isinstance(x, dict):
        keys = names if names is not None else [None] * len(values)
        return {"" if key is None else str(key): item for key, item in zip(keys, values)}
    if isinstance(x, RList) or names is not None:
        return RList(values, names)
    return values


def inset2(x: Any, index: Any, value: Any) -> Any:
    """``[[<-``. Replace or append one element. The input is not modified."""

    if isinstance(x, Matrix):
        raise TypeError("inset2 expects a vector or a list")
    values, names = _values_and_names(x)
    if isinstance(index, str):
        current = [] if names is None else list(names)
        hits = [i for i, got in enumerate(current) if got == index]
        if hits:
            values[hits[0]] = value
            return _restore(x, values, names)
        values.append(value)
        if names is None and not isinstance(x, (RList, Vector, dict)):
            return values
        base = current if current else [None] * (len(values) - 1)
        return _restore(x, values, base + [index])
    kind, spec = _normalize_index(index)
    if kind != "integer" or spec is None or len(spec) != 1 or spec[0] is None or spec[0] < 1:
        message = "attempt to select less than one element" if spec and spec[0] == 0 else "subscript out of bounds"
        raise IndexError(message)
    pos = spec[0]
    if pos > len(values):
        gap = pos - len(values)
        values = values + [_missing_value(values) for _ in range(gap - 1)] + [value]
        if names is not None:
            names = list(names) + [None] * gap
    else:
        values[pos - 1] = value
    return _restore(x, values, names)


def _as_named_carrier(x: Any) -> Vector | Matrix | RList:
    if isinstance(x, (Vector, Matrix, RList)):
        return x.copy()
    values, names = _values_and_names(x)
    return Vector(values, names)


def set_names(x: Any, value: Any) -> Any:
    """``names<-``. A short name vector is padded with missing names. A long one is an error."""

    if isinstance(x, Matrix):
        raise TypeError("set_names expects a vector or a list")
    carrier = _as_named_carrier(x)
    if isinstance(carrier, Matrix):
        raise TypeError("set_names expects a vector or a list")
    if value is None:
        carrier.names = None
        return carrier
    incoming = [value] if isinstance(value, str) else list(value)
    n = len(carrier.values)
    if len(incoming) > n:
        raise ValueError(
            f"'names' attribute [{len(incoming)}] must be the same length as the vector [{n}]"
        )
    if len(incoming) < n:
        incoming = incoming + [None] * (n - len(incoming))
    carrier.names = [None if name is None else str(name) for name in incoming]
    return carrier


def set_colnames(x: Any, value: Any) -> Matrix:
    """``colnames<-``. ``value`` must have one name per column."""

    if not isinstance(x, Matrix):
        raise TypeError("set_colnames expects a matrix")
    out = x.copy()
    out.colnames = _dimnames(value, out.data.shape[1], "col")
    return out


def set_rownames(x: Any, value: Any) -> Matrix:
    """``rownames<-``. ``value`` must have one name per row."""

    if not isinstance(x, Matrix):
        raise TypeError("set_rownames expects a matrix")
    out = x.copy()
    out.rownames = _dimnames(value, out.data.shape[0], "row")
    return out


def set_class(x: Any, value: Any) -> Vector:
    """``class<-``. ``value`` is one class name or a list of them."""

    if isinstance(x, Matrix):
        raise TypeError("set_class expects a vector")
    carrier = _as_named_carrier(x)
    if not isinstance(carrier, Vector):
        raise TypeError("set_class expects a vector")
    carrier.r_class = _class_list(value)
    return carrier


def set_attr(x: Any, which: str, value: Any) -> Any:
    """``attr<-``. ``which`` selects the attribute. ``names`` and ``class`` update those slots."""

    if which == "names":
        return set_names(x, value)
    if which == "class":
        return set_class(x, value)
    if which == "colnames":
        return set_colnames(x, value)
    if which == "rownames":
        return set_rownames(x, value)
    if isinstance(x, Matrix):
        raise TypeError("set_attr on a matrix supports colnames and rownames")
    carrier = _as_named_carrier(x)
    if not isinstance(carrier, Vector):
        raise TypeError("set_attr expects a vector")
    if value is None:
        carrier.attributes.pop(which, None)
    else:
        carrier.attributes[which] = value
    return carrier


def set_attributes(x: Any, value: Any) -> Vector:
    """``attributes<-``. Replace every attribute. ``names`` and ``class`` are read from ``value``."""

    if isinstance(x, Matrix):
        raise TypeError("set_attributes expects a vector")
    values, _names = _values_and_names(x)
    out = Vector(values)
    if value is None:
        return out
    if not isinstance(value, dict):
        raise TypeError("set_attributes expects a dict of attributes, or None")
    for key, item in value.items():
        if key == "names":
            named = set_names(out, item)
            out.names = named.names
        elif key == "class":
            out.r_class = _class_list(item)
        else:
            out.attributes[key] = item
    return out
