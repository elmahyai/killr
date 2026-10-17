"""Extract grouping factors from models and data (nlme ``getGroups``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from nlme.balancedgrouped import BalancedGroupedData


@dataclass(frozen=True, slots=True)
class GroupFactor:
    """Factor result comparable to R's ``factor`` / ``ordered``."""

    codes: np.ndarray
    levels: tuple[str, ...]
    ordered: bool = False
    label: str | None = None

    def __array__(self, dtype=None, copy=None):
        if dtype is None:
            dtype = np.float64
        return np.asarray(self.codes, dtype=dtype, copy=copy)


@dataclass(slots=True)
class Lme:
    """``lme`` stand-in for ``getGroups.lme``."""

    groups: np.ndarray
    group_names: tuple[str, ...] = ("Subject",)
    dims: dict[str, int] | None = None
    classes: tuple[str, ...] = ("lme",)


@dataclass(slots=True)
class Gls:
    """``gls`` stand-in for ``getGroups.gls``."""

    groups: Any
    classes: tuple[str, ...] = ("gls",)


@dataclass(slots=True)
class LmList:
    """``lmList`` stand-in for ``getGroups.lmList``."""

    groups: Any
    classes: tuple[str, ...] = ("lmList",)


@dataclass(slots=True)
class CorStruct:
    """``corStruct`` stand-in for ``getGroups.corStruct``."""

    groups: Any | None = None
    classes: tuple[str, ...] = ("corStruct",)


@dataclass(slots=True)
class VarFunc:
    """``varFunc`` stand-in for ``getGroups.varFunc``."""

    groups: Any | None = None
    classes: tuple[str, ...] = ("varFunc",)


@dataclass(slots=True)
class GroupedDataFrame:
    """``groupedData`` / ``data.frame`` stand-in for ``getGroups.data.frame``."""

    columns: dict[str, np.ndarray]
    formula: str | None = None
    classes: tuple[str, ...] = ("nfnGroupedData", "nfGroupedData", "groupedData", "data.frame")
    group_levels: tuple[str, ...] | None = None


def getGroups(object, form=None, level=None, data=None, sep="/"):
    """Extract grouping factors from ``object``."""
    del data  # R's data.frame method rejects this argument
    classes = _class_vector(object)
    if "lme" in classes:
        return _get_groups_lme(object, level)
    if "gls" in classes:
        return _get_groups_gls(object)
    if "lmList" in classes:
        return _get_groups_lmlist(object)
    if "corStruct" in classes:
        raise TypeError("corStruct getGroups requires a data argument in R")
    if "varFunc" in classes:
        return _get_groups_varfunc(object)
    if isinstance(object, BalancedGroupedData) or "groupedData" in classes or "data.frame" in classes:
        if form is None:
            form = _default_formula(object)
        return _get_groups_data_frame(object, form, level, sep)
    shown = _show_classes(classes)
    raise TypeError(f"no applicable method for 'getGroups' applied to an object of class {shown}")


def _get_groups_lme(obj: Lme, level: Any) -> GroupFactor:
    q = 1
    if obj.dims is not None and "Q" in obj.dims:
        q = int(obj.dims["Q"])
    if level is None:
        level = q
    if isinstance(obj.groups, GroupFactor):
        column = obj.groups
    else:
        groups = np.asarray(obj.groups)
        if groups.ndim == 1:
            values = groups
        else:
            col_index = _resolve_level(level, obj.group_names, groups.shape[1])
            values = groups[:, col_index]
        column = GroupFactor(np.asarray(values, dtype=np.float64), (), ordered=True)
    label = None
    if isinstance(level, int) or (isinstance(level, float) and float(level).is_integer()):
        index = int(level)
        if index == q and len(obj.group_names) >= index:
            label = obj.group_names[index - 1]
    return GroupFactor(column.codes, column.levels, column.ordered, label=label)


def _get_groups_gls(obj: Gls) -> Any:
    return obj.groups


def _get_groups_lmlist(obj: LmList) -> Any:
    return obj.groups


def _get_groups_varfunc(obj: VarFunc) -> Any:
    return getattr(obj, "groups", None)


def _get_groups_data_frame(object, form, level: Any, sep: str) -> GroupFactor | np.ndarray:
    if isinstance(object, BalancedGroupedData):
        return _get_groups_balanced(object)
    frame = _as_grouped_frame(object)
    grp_form = _groups_formula(form, sep=sep, as_list=True)
    if grp_form is None:
        rhs = _formula_rhs(form)
        if rhs is None:
            raise ValueError("'form' can only be a formula, or a list of formulas")
        grp_form = _split_groups(rhs, sep)
    if isinstance(grp_form, dict):
        names = list(grp_form.keys())
        vectors = []
        nrow = _nrow(frame)
        for name in names:
            vectors.append(_eval_group_var(grp_form[name], frame, nrow))
        if len(vectors) == 1:
            return vectors[0]
        return _combine_group_frame(vectors, names, frame, level, sep)
    raise ValueError("'form' can only be a formula, or a list of formulas")


def _get_groups_balanced(object: BalancedGroupedData) -> GroupFactor:
    codes = np.asarray(object.columns[object.group_name], dtype=np.float64)
    return GroupFactor(codes, tuple(object.group_levels), ordered=True)


def _as_grouped_frame(object) -> GroupedDataFrame:
    if isinstance(object, GroupedDataFrame):
        return object
    if isinstance(object, BalancedGroupedData):
        return GroupedDataFrame(object.columns, object.formula, object.classes, object.group_levels)
    raise TypeError("expected grouped data frame stand-in")


def _default_formula(object) -> str:
    if hasattr(object, "formula") and object.formula:
        return str(object.formula).strip()
    raise ValueError("formula(object) must return a formula")


def _groups_formula(form, sep: str, as_list: bool):
    if isinstance(form, dict):
        return form
    text = _formula_text(form)
    if text is None:
        raise ValueError("'form' argument must be a formula")
    if "|" not in text.split("~", 1)[1]:
        return None
    rhs = text.split("|", 1)[1].strip()
    if not as_list:
        return f"~{rhs}"
    return _split_groups(rhs, sep)


def _split_groups(rhs: str, sep: str) -> dict[str, str]:
    parts = [part.strip() for part in rhs.split(sep) if part.strip()]
    return {name: f"~{name}" for name in parts}


def _formula_rhs(form) -> str | None:
    text = _formula_text(form)
    if text is None:
        return None
    return text.split("~", 1)[1].strip()


def _formula_text(form) -> str | None:
    if isinstance(form, str) and "~" in form:
        return form.strip()
    if hasattr(form, "formula"):
        value = form.formula
        if isinstance(value, str) and "~" in value:
            return value.strip()
    return None


def _eval_group_var(formula: str, frame: GroupedDataFrame, nrow: int) -> GroupFactor:
    name = formula.strip().lstrip("~").strip()
    if name not in frame.columns:
        raise KeyError(name)
    values = np.asarray(frame.columns[name])
    if len(values) == 1:
        values = np.repeat(values, nrow)
    levels = frame.group_levels
    if levels is not None:
        return GroupFactor(np.asarray(values, dtype=np.float64), tuple(levels), ordered=True)
    return _as_factor(values)


def _as_factor(values: np.ndarray) -> GroupFactor:
    text = [str(item) for item in values]
    levels = []
    for item in text:
        if item not in levels:
            levels.append(item)
    codes = np.array([levels.index(item) + 1 for item in text], dtype=np.float64)
    return GroupFactor(codes, tuple(levels), ordered=False)


def _combine_group_frame(vectors, names, frame, level, sep):
    base = np.column_stack([np.asarray(item.codes, dtype=np.float64) for item in vectors])
    if level is None:
        return base
    col_index = _resolve_level(level, names, base.shape[1])
    if isinstance(col_index, slice):
        chosen = base[:, col_index]
    else:
        chosen = base[:, [col_index]]
    if chosen.shape[1] == 1:
        return GroupFactor(chosen[:, 0], vectors[col_index].levels, vectors[col_index].ordered)
    pasted = np.array(["/".join(str(part) for part in row) for row in chosen], dtype=object)
    return _as_factor(pasted)


def _resolve_level(level: Any, names: Sequence[str], ncols: int) -> int | slice:
    if isinstance(level, str):
        if level not in names:
            raise ValueError(f"level of {level!r} does not match formula")
        return names.index(level)
    index = int(level)
    if index < 1 or index > ncols:
        raise ValueError(f"level of {level!r} does not match formula")
    return index - 1


def _nrow(frame: GroupedDataFrame) -> int:
    first = next(iter(frame.columns.values()))
    return len(first)


def _class_vector(object: Any) -> tuple[str, ...]:
    classes = getattr(object, "classes", None)
    if classes is not None:
        return tuple(classes)
    return (type(object).__name__,)


def _show_classes(classes: tuple[str, ...]) -> str:
    if len(classes) == 1:
        return f'"{classes[0]}"'
    inner = ", ".join(f"'{name}'" for name in classes)
    return f'"c({inner})"'
