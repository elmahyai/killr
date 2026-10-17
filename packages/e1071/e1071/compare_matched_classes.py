"""Compare classifications after optimal label matching (e1071 ``compareMatchedClasses``)."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from e1071.match_classes import match_classes
from e1071.patterns import class_agreement


def _as_label_matrix(x: Any) -> list[list[Any]]:
    if x is None:
        return [[]]
    if isinstance(x, Mapping):
        raise TypeError("x must be a matrix-like object")
    rows = list(x)
    if not rows:
        return [[]]
    if not isinstance(rows[0], (list, tuple)):
        return [[value] for value in rows]
    return [list(row) for row in rows]


def _table_levels(a: Sequence[Any], b: Sequence[Any]) -> list[Any]:
    return sorted(set(a) | set(b), key=lambda value: (str(type(value)), value))


def _cross_table(a: Sequence[Any], b: Sequence[Any]) -> tuple[list[list[float]], list[str], list[str]]:
    row_levels = _table_levels(a, b)
    col_levels = list(row_levels)
    row_names = [str(level) for level in row_levels]
    col_names = [str(level) for level in col_levels]
    counts = [[0.0 for _ in col_levels] for _ in row_levels]
    row_index = {level: index for index, level in enumerate(row_levels)}
    col_index = {level: index for index, level in enumerate(col_levels)}
    for left, right in zip(a, b, strict=True):
        counts[row_index[left]][col_index[right]] += 1.0
    return counts, row_names, col_names


def _resolve_column_index(colnames: Sequence[str], assigned: Any) -> int:
    if isinstance(assigned, bool):
        return colnames.index(str(assigned))
    if isinstance(assigned, (int, float)) and not isinstance(assigned, bool):
        if float(assigned).is_integer():
            return int(assigned) - 1
    text = str(assigned)
    if text in colnames:
        return colnames.index(text)
    raise ValueError("invalid column assignment from matchClasses")


def _reorder_tab(tab: list[list[float]], rownames: Sequence[str], colnames: Sequence[str], matching: Mapping[str, Any]) -> list[list[float]]:
    order = [_resolve_column_index(colnames, matching[str(name)]) for name in rownames]
    return [[row[index] for index in order] for row in tab]


def _empty_matrix(nrow: int, ncol: int) -> list[list[float]]:
    return [[math.nan for _ in range(ncol)] for _ in range(nrow)]


def _fill_agreement(
    target: dict[str, list[list[float]]],
    row: int,
    col: int,
    tab: list[list[float]],
    rownames: Sequence[str],
    colnames: Sequence[str],
    *,
    method: str,
    iter: int,
    maxexact: int,
    verbose: bool,
) -> None:
    matching = match_classes(
        tab,
        method=method,
        iter=iter,
        maxexact=maxexact,
        verbose=verbose,
        rownames=rownames,
        colnames=colnames,
    )
    matched = _reorder_tab(tab, rownames, colnames, matching)
    diag, kappa, rand, crand = class_agreement(matched)
    target["diag"][row][col] = diag
    target["kappa"][row][col] = kappa
    target["rand"][row][col] = rand
    target["crand"][row][col] = crand


def compareMatchedClasses(
    x,
    y=None,
    method: str = "rowmax",
    iter: int = 1,
    maxexact: int = 9,
    verbose: bool = False,
):
    """Compare two (or several) matched labelings using ``matchClasses`` and ``classAgreement``."""
    matrix_x = _as_label_matrix(x)
    ncol_x = len(matrix_x[0]) if matrix_x and matrix_x[0] else 0
    if any(len(row) != ncol_x for row in matrix_x):
        raise ValueError("x must be a rectangular matrix")

    if y is None:
        retval = {
            "diag": _empty_matrix(ncol_x, ncol_x),
            "kappa": _empty_matrix(ncol_x, ncol_x),
            "rand": _empty_matrix(ncol_x, ncol_x),
            "crand": _empty_matrix(ncol_x, ncol_x),
        }
        for k in range(ncol_x - 1):
            col_k = [row[k] for row in matrix_x]
            for l in range(k + 1, ncol_x):
                col_l = [row[l] for row in matrix_x]
                tab, rownames, colnames = _cross_table(col_k, col_l)
                _fill_agreement(
                    retval,
                    k,
                    l,
                    tab,
                    rownames,
                    colnames,
                    method=method,
                    iter=iter,
                    maxexact=maxexact,
                    verbose=verbose,
                )
        return retval

    matrix_y = _as_label_matrix(y)
    ncol_y = len(matrix_y[0]) if matrix_y and matrix_y[0] else 0
    if any(len(row) != ncol_y for row in matrix_y):
        raise ValueError("y must be a rectangular matrix")
    if len(matrix_x) != len(matrix_y):
        raise ValueError("x and y must have the same number of rows")

    retval = {
        "diag": _empty_matrix(ncol_x, ncol_y),
        "kappa": _empty_matrix(ncol_x, ncol_y),
        "rand": _empty_matrix(ncol_x, ncol_y),
        "crand": _empty_matrix(ncol_x, ncol_y),
    }
    for k in range(ncol_x):
        col_k = [row[k] for row in matrix_x]
        for l in range(ncol_y):
            col_l = [row[l] for row in matrix_y]
            tab, rownames, colnames = _cross_table(col_k, col_l)
            _fill_agreement(
                retval,
                k,
                l,
                tab,
                rownames,
                colnames,
                method=method,
                iter=iter,
                maxexact=maxexact,
                verbose=verbose,
            )
    return retval
