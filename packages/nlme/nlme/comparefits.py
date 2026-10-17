"""Compare coefficient tables from fitted objects (nlme compareFits)."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import FrameType

import numpy as np


@dataclass(frozen=True, slots=True)
class CompareFitsArray:
    """Three-dimensional compareFits result with R-style dimnames."""

    values: np.ndarray
    row_names: tuple[str, ...]
    object_labels: tuple[str, str]
    col_names: tuple[str, ...]

    def __array__(self, dtype=None, copy=None):
        if dtype is None:
            dtype = np.float64
        return np.asarray(self.values, dtype=dtype, copy=copy)


@dataclass(frozen=True, slots=True)
class NamedMatrix:
    """Matrix with row and column names, as from ``coef`` on ``lmList`` objects."""

    values: np.ndarray
    rownames: tuple[str, ...]
    colnames: tuple[str, ...]

    def __array__(self, dtype=None, copy=None):
        if dtype is None:
            dtype = np.float64
        return np.asarray(self.values, dtype=dtype, copy=copy)


@dataclass(frozen=True, slots=True)
class _Tabular:
    values: np.ndarray
    row_names: tuple[str, ...] | None
    col_names: tuple[str, ...] | None


def compareFits(object1, object2, which=None) -> CompareFitsArray:
    """Align two coefficient tables and stack them for element-wise comparison."""
    caller = inspect.currentframe()
    try:
        call_frame = caller.f_back if caller is not None else None
        label1 = _deparsed_argument("object1", call_frame)
        label2 = _deparsed_argument("object2", call_frame)
    finally:
        del caller

    tab1 = _as_tabular(object1)
    tab2 = _as_tabular(object2)
    if which is None:
        which = list(range(1, tab1.values.shape[1] + 1))

    tab1, tab2 = _align_columns(tab1, tab2)
    _check_row_names(tab1.row_names, tab2.row_names)
    tab2 = _reorder_rows(tab2, tab1.row_names, tab1.col_names)
    tab1, tab2 = _subset_columns(tab1, tab2, which)

    row_names = tab1.row_names or tuple(str(index) for index in range(tab1.values.shape[0]))
    col_names = tab1.col_names or tuple(str(index) for index in range(tab1.values.shape[1]))
    out = np.zeros(
        (tab1.values.shape[0], 2, tab1.values.shape[1]), dtype=np.float64, order="F"
    )
    for index, name in enumerate(col_names):
        out[:, 0, index] = _column_values(tab1, name, index)
        out[:, 1, index] = _column_values(tab2, name, index)

    return CompareFitsArray(out, row_names, (label1, label2), col_names)


def _as_tabular(object) -> _Tabular:
    if isinstance(object, _Tabular):
        return object
    if isinstance(object, CompareFitsArray):
        raise TypeError("compareFits expects two-dimensional coefficient tables")
    if isinstance(object, NamedMatrix):
        return _Tabular(
            np.array(object.values, dtype=np.float64, copy=True),
            object.rownames,
            object.colnames,
        )
    values = np.asarray(object, dtype=np.float64)
    if values.ndim != 2:
        raise TypeError("compareFits expects two-dimensional coefficient tables")
    row_names = _dimnames(object, axis=0, size=values.shape[0])
    col_names = _dimnames(object, axis=1, size=values.shape[1])
    return _Tabular(np.array(values, copy=True), row_names, col_names)


def _dimnames(object, axis: int, size: int) -> tuple[str, ...] | None:
    names = getattr(object, "rownames", None) if axis == 0 else getattr(object, "colnames", None)
    if names is None and hasattr(object, "dimnames"):
        dimnames = object.dimnames
        if isinstance(dimnames, (list, tuple)) and len(dimnames) > axis:
            names = dimnames[axis]
    if names is None:
        return None
    seq = tuple(str(name) for name in names)
    if len(seq) != size:
        raise ValueError("dimnames length does not match array extent")
    return seq


def _align_columns(tab1: _Tabular, tab2: _Tabular) -> tuple[_Tabular, _Tabular]:
    names1 = list(tab1.col_names or [str(index + 1) for index in range(tab1.values.shape[1])])
    names2 = list(tab2.col_names or [str(index + 1) for index in range(tab2.values.shape[1])])
    values1 = tab1.values
    values2 = tab2.values
    nrow = values1.shape[0]
    na_column = np.full(nrow, np.nan, dtype=np.float64)

    for name in names2:
        if name not in names1:
            names1.append(name)
            values1 = np.column_stack((values1, na_column))

    for name in names1:
        if name not in names2:
            names2.append(name)
            values2 = np.column_stack((values2, na_column))

    return (
        _Tabular(values1, tab1.row_names, tuple(names1)),
        _Tabular(values2, tab2.row_names, tuple(names2)),
    )


def _check_row_names(
    row_names1: tuple[str, ...] | None, row_names2: tuple[str, ...] | None
) -> None:
    if row_names1 is None or row_names2 is None:
        return
    if sorted(row_names1) != sorted(row_names2):
        raise ValueError("objects must have coefficients with same row names")


def _reorder_rows(
    tab: _Tabular, row_order: tuple[str, ...] | None, col_order: tuple[str, ...]
) -> _Tabular:
    if row_order is None or tab.row_names is None:
        return tab
    row_index = {name: index for index, name in enumerate(tab.row_names)}
    rows = np.array([row_index[name] for name in row_order], dtype=np.intp)
    col_index = {name: index for index, name in enumerate(tab.col_names or ())}
    cols = np.array([col_index[name] for name in col_order], dtype=np.intp)
    return _Tabular(tab.values[np.ix_(rows, cols)], row_order, col_order)


def _subset_columns(
    tab1: _Tabular, tab2: _Tabular, which
) -> tuple[_Tabular, _Tabular]:
    selector = _column_selector(tab1, which)
    return (
        _Tabular(tab1.values[:, selector], tab1.row_names, _selected_colnames(tab1, selector)),
        _Tabular(tab2.values[:, selector], tab2.row_names, _selected_colnames(tab2, selector)),
    )


def _column_selector(tab: _Tabular, which) -> np.ndarray:
    if isinstance(which, (str, bytes)):
        which = [which]
    which = list(which)
    if not which:
        return np.array([], dtype=np.intp)
    if isinstance(which[0], str):
        names = tab.col_names or tuple(str(index + 1) for index in range(tab.values.shape[1]))
        lookup = {name: index for index, name in enumerate(names)}
        missing = [name for name in which if name not in lookup]
        if missing:
            raise ValueError(f"unknown column names: {', '.join(missing)}")
        return np.array([lookup[name] for name in which], dtype=np.intp)
    indices = [int(index) for index in which]
    if any(index < 1 or index > tab.values.shape[1] for index in indices):
        raise ValueError(f"'which' must be between 1 and {tab.values.shape[1]}")
    return np.array([index - 1 for index in indices], dtype=np.intp)


def _selected_colnames(tab: _Tabular, selector: np.ndarray) -> tuple[str, ...]:
    names = tab.col_names or tuple(str(index + 1) for index in range(tab.values.shape[1]))
    return tuple(names[index] for index in selector)


def _column_values(tab: _Tabular, name: str, position: int) -> np.ndarray:
    if tab.col_names is not None:
        index = tab.col_names.index(name)
        return tab.values[:, index]
    return tab.values[:, position]


def _deparsed_argument(name: str, caller: FrameType | None) -> str:
    if caller is None:
        return name
    for key, value in caller.f_locals.items():
        if key == name:
            return key
    return name
