"""Summarize a data frame by the levels of a grouping factor (nlme ``gsummary``)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from nlme.groupeddata import DataFrame, Factor, get_groups, group_terms

__all__ = ["gsummary"]


def _mean_na_rm(x) -> float:
    """``function(x) mean(x, na.rm = TRUE)``."""
    values = np.asarray(x, dtype=np.float64)
    values = values[~np.isnan(values)]
    if values.size == 0:
        return float("nan")
    return float(np.mean(values))


def _mode(values: list[str]) -> str:
    """``Mode``: the most frequent value; ties go to the first name in sorted order."""
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    best_name = ""
    best_count = -1
    for name in sorted(counts):
        if counts[name] > best_count:
            best_name, best_count = name, counts[name]
    return best_name


def _functions(FUN) -> dict[str, Callable[..., Any]]:
    """Per-class summary functions: numeric uses ``FUN``; ordered and factor use ``Mode``."""
    table: dict[str, Callable[..., Any]] = {"numeric": _mean_na_rm, "ordered": _mode, "factor": _mode}
    if FUN is None:
        return table
    if isinstance(FUN, Mapping):
        for key, value in FUN.items():
            table[key] = value
        return table
    table["numeric"] = FUN
    return table


def _take(column, rows: np.ndarray):
    if isinstance(column, Factor):
        return column.subset(rows)
    return np.asarray(column)[rows]


def _differs(column, reference) -> bool:
    if isinstance(column, Factor):
        return bool(np.any(column.codes != reference.codes))
    values = np.asarray(column, dtype=np.float64)
    ref = np.asarray(reference, dtype=np.float64)
    equal = (values == ref) | (np.isnan(values) & np.isnan(ref))
    return bool(np.any(~equal))


def gsummary(
    object: DataFrame,
    FUN=None,
    omitGroupingFactor: bool = False,
    form: str | None = None,
    level: int | None = None,
    groups: Factor | list | tuple | None = None,
    invariantsOnly: bool = False,
) -> DataFrame | None:
    """Summarize ``object`` by group (R's ``gsummary``).

    Each group becomes one row, ordered by the group factor levels. Columns that
    vary within a group are summarized with ``FUN`` (numeric) or ``Mode`` (factor),
    and invariant columns keep their first value. ``FUN`` may be a function or a
    dict with ``numeric``, ``ordered`` and ``factor`` entries.
    """
    if not isinstance(object, DataFrame):
        raise TypeError('object must inherit from class "data.frame"')
    terms: tuple[str, ...] = ()
    if groups is None:
        if form is None:
            form = object.formula
        if form is None:
            raise ValueError("'form' must be a formula")
        terms = group_terms(form)
        if level is None:
            level = len(terms)
        groups = get_groups(object, form, level)
    elif not isinstance(groups, Factor):
        groups = Factor.from_values(groups)
    elif form is not None:
        terms = group_terms(form)

    codes = np.asarray(groups.codes, dtype=np.int64)
    if codes.shape[0] != object.nrow:
        raise ValueError("'groups' must have one value per row of 'object'")

    first_row: dict[int, int] = {}
    for row, code in enumerate(codes.tolist()):
        first_row.setdefault(code, row)
    group_codes = sorted(first_row)
    first_in_group = np.array([first_row[code] for code in group_codes], dtype=np.int64)
    as_first = np.array([first_row[code] for code in codes.tolist()], dtype=np.int64)
    row_names = tuple(groups.levels[code] for code in group_codes)

    value: dict[str, Any] = {
        name: _take(column, first_in_group) for name, column in object.columns.items()
    }
    varying = {
        name: _differs(column, _take(column, as_first)) for name, column in object.columns.items()
    }

    if any(varying.values()) and not invariantsOnly:
        fun = _functions(FUN)
        for name, column in object.columns.items():
            if not varying[name]:
                continue
            rows_by_group = [np.nonzero(codes == code)[0] for code in group_codes]
            if isinstance(column, Factor):
                kind = "ordered" if column.ordered else "factor"
                texts = column.texts()
                summary = [fun[kind]([texts[row] for row in rows]) for rows in rows_by_group]
                used = [level for level in column.levels if level in set(summary)]
                position = {level: pos for pos, level in enumerate(used)}
                value[name] = Factor(
                    np.array([position[item] for item in summary], dtype=np.int64),
                    tuple(used),
                    ordered=column.ordered,
                )
            else:
                numeric = np.asarray(column, dtype=np.float64)
                value[name] = np.array(
                    [float(fun["numeric"](numeric[rows])) for rows in rows_by_group],
                    dtype=np.float64,
                )
    else:
        value = {name: column for name, column in value.items() if not varying[name]}

    if omitGroupingFactor:
        if form is None:
            raise ValueError("cannot omit grouping factor without 'form'")
        grp_level = len(terms) if level is None else int(level)
        grp_name = terms[grp_level - 1]
        keep = {name: column for name, column in value.items() if name != grp_name}
        if not keep:
            return None
        value = keep

    return DataFrame(columns=value, attributes={"row.names": row_names}, classes=("data.frame",))
