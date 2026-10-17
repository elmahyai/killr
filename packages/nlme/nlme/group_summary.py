"""Group extraction and ``gsummary`` for augmented predictions."""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

import numpy as np

from nlme.fit_objects import LmeFit, LmListFit
from nlme.getcovariateformula import getCovariateFormula


def get_groups_lme(object: LmeFit, level: int | Sequence[int] = 1) -> np.ndarray:
    if isinstance(level, (list, tuple)):
        if len(level) != 1:
            raise ValueError("only one level implemented for getGroups.lme")
        level = level[0]
    name = object.group_colnames[level - 1]
    return np.asarray(object.groups[name], dtype=np.object_)


def get_groups_lm_list(object: LmListFit) -> np.ndarray:
    if object.groups_vector is not None:
        return np.asarray(object.groups_vector, dtype=np.object_)
    raise ValueError("lmList object missing groups vector")


def get_covariate_data_frame(formula: str, frame: dict[str, list[Any]]) -> np.ndarray:
    cov = getCovariateFormula(formula)
    var = cov.text.lstrip("~").strip()
    if not var or var == "1":
        return np.ones(len(next(iter(frame.values()))), dtype=np.float64)
    return np.asarray(frame[var], dtype=np.float64)


def gsummary(
    object: dict[str, list[Any]],
    *,
    groups: np.ndarray,
    invariants_only: bool = False,
) -> tuple[dict[str, list[Any]], tuple[str, ...]]:
    """Group-wise summary columns (numeric means, mode for factors)."""
    del invariants_only
    group_list = [str(item) for item in groups]
    unique_groups = list(dict.fromkeys(group_list))
    first_in_group = [group_list.index(name) for name in unique_groups]
    group_to_first = {name: index for name, index in zip(unique_groups, first_in_group, strict=True)}
    as_first = [group_to_first[name] for name in group_list]

    value: dict[str, list[Any]] = {
        column: [values[index] for index in first_in_group]
        for column, values in object.items()
    }
    row_order = sorted(range(len(unique_groups)), key=lambda index: str(unique_groups[index]))
    unique_groups = [unique_groups[index] for index in row_order]
    value = {column: [values[index] for index in row_order] for column, values in value.items()}

    varying: dict[str, bool] = {}
    for column, values in object.items():
        aux = [str(item) for item in values]
        ref = [aux[index] for index in as_first]
        varying[column] = any(a != b for a, b in zip(aux, ref, strict=True))

    for column, is_varying in varying.items():
        if not is_varying:
            continue
        raw = object[column]
        if _is_numeric_column(raw):
            means = []
            for group in unique_groups:
                subset = [float(raw[index]) for index, name in enumerate(group_list) if name == group]
                means.append(float(np.mean(subset)))
            value[column] = means
        else:
            modes = []
            for group in unique_groups:
                subset = [str(raw[index]) for index, name in enumerate(group_list) if name == group]
                modes.append(_mode(subset))
            value[column] = modes

    if not any(varying.values()):
        drop = [column for column, is_varying in varying.items() if not is_varying]
        for column in drop:
            if column in value:
                del value[column]
    return value, tuple(str(name) for name in unique_groups)


def _is_numeric_column(values: list[Any]) -> bool:
    for value in values:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            continue
        return False
    return True


def _mode(values: list[str]) -> str:
    counts = Counter(values)
    best = max(counts.values())
    for value in values:
        if counts[value] == best:
            return value
    return values[0]
