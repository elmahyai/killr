"""Tabular response layout for balanced grouped data (nlme asTable)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class GroupedData:
    """Minimal groupedData stand-in for ``asTable``."""

    response: tuple[float, ...]
    covariate: tuple[float, ...]
    groups: tuple[str, ...]
    group_levels: tuple[str, ...]
    covariate_levels: tuple[float, ...] | None = None
    n_group_formula_levels: int = 1


@dataclass(frozen=True, slots=True)
class Table:
    """Matrix of response values by group and covariate level."""

    values: np.ndarray
    row_names: tuple[str, ...]
    col_names: tuple[str, ...]

    def __str__(self) -> str:
        width = max((len(name) for name in self.col_names), default=0)
        lines = [f"{'':>{width}} " + " ".join(f"{name:>4}" for name in self.col_names)]
        for row_name, row in zip(self.row_names, self.values):
            body = " ".join(f"{value:4.1f}" for value in row)
            lines.append(f"{row_name:>{width}} {body}")
        return "\n".join(lines)


def asTable(data):
    """Convert balanced grouped data to a response matrix."""
    n_levels = _n_group_formula_levels(data)
    if n_levels > 1:
        raise ValueError("'asTable' cannot be used with multilevel grouped data")

    groups = np.asarray(_groups(data), dtype=np.object_)
    covariate = np.asarray(_covariate(data), dtype=float)
    response = np.asarray(_response(data), dtype=float)

    group_levels = tuple(_group_levels(data, groups))
    covariate_levels = tuple(_covariate_levels(data, covariate))

    counts = np.zeros((len(group_levels), len(covariate_levels)), dtype=float)
    g_index = {level: index for index, level in enumerate(group_levels)}
    c_index = {level: index for index, level in enumerate(covariate_levels)}
    for group, cov in zip(groups, covariate, strict=True):
        counts[g_index[str(group)], c_index[float(cov)]] += 1.0

    if counts.size == 0 or len(np.unique(counts)) != 1:
        raise ValueError("'asTable' can only be used with balanced 'groupedData' objects")

    group_codes = np.fromiter(
        (g_index[str(group)] for group in groups),
        dtype=np.intp,
        count=len(groups),
    )
    order = np.lexsort((group_codes, covariate))
    sorted_response = response[order]

    values = np.zeros_like(counts, order="F")
    values.ravel(order="F")[:] = sorted_response

    col_names = tuple(_format_covariate_label(level) for level in covariate_levels)
    return Table(values, group_levels, col_names)


def _n_group_formula_levels(object) -> int:
    if isinstance(object, GroupedData):
        return object.n_group_formula_levels
    return int(getattr(object, "n_group_formula_levels", 1))


def _response(object):
    if isinstance(object, GroupedData):
        return object.response
    return object.response


def _covariate(object):
    if isinstance(object, GroupedData):
        return object.covariate
    return object.covariate


def _groups(object):
    if isinstance(object, GroupedData):
        return object.groups
    return object.groups


def _group_levels(object, groups):
    if isinstance(object, GroupedData):
        return object.group_levels
    levels = getattr(object, "group_levels", None)
    if levels is not None:
        return tuple(levels)
    seen = set()
    out = []
    for name in groups:
        text = str(name)
        if text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _covariate_levels(object, covariate):
    if isinstance(object, GroupedData) and object.covariate_levels is not None:
        return object.covariate_levels
    levels = getattr(object, "covariate_levels", None)
    if levels is not None:
        return tuple(float(level) for level in levels)
    return tuple(sorted({float(value) for value in covariate}))


def _format_covariate_label(level: float) -> str:
    if float(level).is_integer():
        return str(int(level))
    return str(level)
