"""Create groupedData from a balanced matrix (nlme balancedGrouped)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nlme.astable import Table


@dataclass(slots=True)
class BalancedGroupedData:
    """Balanced groupedData stand-in returned by ``balancedGrouped``."""

    columns: dict[str, np.ndarray]
    group_name: str
    group_levels: tuple[str, ...]
    labels: dict[str, str] | None
    units: dict[str, str] | None
    formula: str

    def __getattr__(self, name: str) -> np.ndarray:
        try:
            return self.columns[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def balancedGrouped(form, data, labels=None, units=None) -> BalancedGroupedData:
    """Build a balanced groupedData object from a response matrix."""
    response_name, covariate_name, group_name = _split_grouped_formula(form)
    values, covariate_levels, group_levels_raw = _matrix_layout(data)
    values = np.asarray(values, dtype=np.float64).T

    covariate_levels = _maybe_numeric_levels(covariate_levels)
    rows = _expand_grid(covariate_levels, group_levels_raw)
    response = np.asarray(values, dtype=np.float64).ravel(order="F")

    covariate = np.array([row[0] for row in rows], dtype=np.float64)
    groups = np.array([row[1] for row in rows], dtype=object)
    ordered_levels = _order_group_levels(response, groups)

    columns = {
        covariate_name: covariate,
        group_name: _group_codes(groups, ordered_levels),
        response_name: response,
    }
    return BalancedGroupedData(
        columns=columns,
        group_name=group_name,
        group_levels=ordered_levels,
        labels=labels,
        units=units,
        formula=_formula_text(form),
    )


def _formula_text(form) -> str:
    if isinstance(form, str):
        return form.strip()
    return str(form).strip()


def _split_grouped_formula(form) -> tuple[str, str, str]:
    text = _formula_text(form)
    if "~" not in text:
        raise ValueError("formula must be two-sided")
    response, rest = text.split("~", 1)
    response = response.strip()
    rest = rest.strip()
    if "|" not in rest:
        raise ValueError("right-hand side of formula must be a conditional expression")
    covariate, group = rest.split("|", 1)
    return response, covariate.strip(), group.strip()


def _matrix_layout(data) -> tuple[np.ndarray, tuple, tuple]:
    if isinstance(data, Table):
        values = np.asarray(data.values, dtype=np.float64)
        group_levels = data.row_names
        covariate_levels = data.col_names
        return values, covariate_levels, group_levels
    array = np.asarray(data, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("data must be a two-dimensional matrix")
    dimnames = getattr(data, "dimnames", None)
    if dimnames is None and hasattr(data, "row_names") and hasattr(data, "col_names"):
        return array, tuple(data.col_names), tuple(data.row_names)
    if dimnames is None:
        raise ValueError("matrix data must have dimnames")
    row_names, col_names = dimnames
    return array, tuple(col_names), tuple(row_names)


def _maybe_numeric_levels(levels: tuple) -> tuple:
    numeric = []
    for level in levels:
        try:
            value = float(level)
        except (TypeError, ValueError):
            return levels
        if np.isnan(value):
            return levels
        numeric.append(value)
    return tuple(numeric)


def _expand_grid(covariate_levels: tuple, group_levels: tuple) -> list[tuple]:
    rows: list[tuple] = []
    for group in group_levels:
        for covariate in covariate_levels:
            rows.append((covariate, group))
    return rows


def _order_group_levels(response: np.ndarray, groups: np.ndarray) -> tuple[str, ...]:
    seen: list[str] = []
    for group in groups:
        key = str(group)
        if key not in seen:
            seen.append(key)
    maxima = []
    for key in seen:
        values = [float(value) for value, group in zip(response, groups, strict=True) if str(group) == key]
        maxima.append(max(values))
    order = sorted(range(len(seen)), key=lambda index: maxima[index])
    return tuple(seen[index] for index in order)


def _group_codes(groups: np.ndarray, levels: tuple[str, ...]) -> np.ndarray:
    index = {level: float(i + 1) for i, level in enumerate(levels)}
    return np.array([index[str(group)] for group in groups], dtype=np.float64)
