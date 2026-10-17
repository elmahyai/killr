"""Apply a function to the subframes of a grouped data frame (nlme ``gapply``)."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from nlme.getgroups import GroupedDataFrame, GroupFactor, getGroups
from nlme.getgroupsformula import getGroupsFormula


def gapply(
    object: GroupedDataFrame,
    which: Any = None,
    FUN: Callable[[GroupedDataFrame], Any] = None,
    form: str | None = None,
    level: int | None = None,
    groups: Any = None,
    **kwargs: Any,
):
    """Apply ``FUN`` to each group's subframe; scalar results are simplified to an array."""
    if not isinstance(object, GroupedDataFrame):
        raise TypeError('object must inherit from class "data.frame"')
    if groups is None:
        if form is None:
            form = object.formula
        if not isinstance(form, str) or "~" not in form:
            raise ValueError("'form' must be a formula")
        grp_form = getGroupsFormula(form, asList=True)
        if grp_form is None:
            grp_form = [(part, f"~{part}") for part in _rhs_groups(form)]
        if level is None:
            level = len(grp_form)
        elif np.size(level) != 1:
            raise ValueError("only one level allowed in 'gapply'")
        groups = getGroups(object, form=form, level=level)
    frame = object
    if which is not None:
        frame = _select_columns(object, which)
    levels, index = _group_index(groups)
    results = []
    for position in range(len(levels)):
        rows = np.flatnonzero(index == position)
        columns = {name: np.asarray(values)[rows] for name, values in frame.columns.items()}
        subframe = GroupedDataFrame(columns, frame.formula, frame.classes, frame.group_levels)
        results.append(FUN(subframe, **kwargs))
    if results and np.ndim(results[0]) == 0:
        return np.asarray([float(item) for item in results], dtype=np.float64)
    return dict(zip(levels, results))


def _rhs_groups(form: str) -> list[str]:
    """Split the right side of a formula without a conditioning bar on ``/``."""
    rhs = form.split("~", 1)[1].strip()
    return [part.strip() for part in rhs.split("/") if part.strip()]


def _select_columns(object: GroupedDataFrame, which: Any) -> GroupedDataFrame:
    names = list(object.columns.keys())
    if isinstance(which, str) or (isinstance(which, (list, tuple)) and which and isinstance(which[0], str)):
        wanted = [which] if isinstance(which, str) else list(which)
        missing = [name for name in wanted if name not in names]
        if missing:
            raise ValueError(f"{','.join(missing)} not matched")
        chosen = wanted
    else:
        numbers = [int(item) for item in np.atleast_1d(which)]
        if any(item < 1 or item > len(names) for item in numbers):
            raise ValueError(f"'which' must be between 1 and {len(names)}")
        chosen = [names[item - 1] for item in numbers]
    columns = {name: object.columns[name] for name in chosen}
    return GroupedDataFrame(columns, object.formula, object.classes, object.group_levels)


def _group_index(groups: Any) -> tuple[tuple[str, ...], np.ndarray]:
    """Factor levels and a zero-based level index for each row (``split`` order)."""
    if isinstance(groups, GroupFactor):
        index = np.asarray(groups.codes, dtype=np.float64).astype(np.int64) - 1
        return tuple(groups.levels), index
    values = [str(item) for item in np.asarray(groups, dtype=object).reshape(-1)]
    levels = tuple(sorted(set(values)))
    lookup = {name: position for position, name in enumerate(levels)}
    return levels, np.asarray([lookup[item] for item in values], dtype=np.int64)
