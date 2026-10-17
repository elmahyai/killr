"""Augmented and comparative predictions (nlme ``augPred``, ``comparePred``)."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import FrameType
from typing import Any, Sequence

import numpy as np

from nlme.fit_objects import LmeFit, LmListFit
from nlme.getcovariateformula import getCovariateFormula
from nlme.getresponseformula import getResponseFormula
from nlme.group_summary import (
    get_covariate_data_frame,
    get_groups_lme,
    get_groups_lm_list,
    gsummary,
)
from nlme.predict_model import (
    get_response_lme,
    get_response_lm_list,
    predict_lme,
    predict_lm_list,
)

_MISSING = object()


@dataclass(slots=True)
class AugPredFrame:
    """Data-frame-like ``augPred`` / ``comparePred`` result."""

    columns: dict[str, np.ndarray]
    column_names: tuple[str, ...]
    type_levels: tuple[str, ...]
    labels: dict[str, str]
    units: dict[str, str]
    formula: str
    classes: tuple[str, ...] = ("augPred", "data.frame")
    group_levels: tuple[str, ...] | None = None

    def flatten_numeric(self) -> np.ndarray:
        parts: list[np.ndarray] = []
        for name in self.column_names:
            column = self.columns[name]
            if name == ".type":
                codes = _ordered_codes(column, self.type_levels)
                parts.append(codes.astype(np.float64))
            elif name == self.column_names[1]:
                codes = _factor_codes(column, self.group_levels)
                parts.append(codes.astype(np.float64))
            else:
                parts.append(np.asarray(column, dtype=np.float64))
        return np.concatenate(parts)


def augPred(
    object,
    primary=_MISSING,
    minimum=_MISSING,
    maximum=_MISSING,
    length_out: int = 51,
    level=_MISSING,
    **kwargs,
) -> AugPredFrame:
    del kwargs
    classes = _class_vector(object)
    if "lme" in classes:
        return _aug_pred_lme(
            object,
            primary=primary,
            minimum=minimum,
            maximum=maximum,
            length_out=length_out,
            level=level,
        )
    if "lmList" in classes:
        return _aug_pred_lm_list(
            object,
            primary=primary,
            minimum=minimum,
            maximum=maximum,
            length_out=length_out,
        )
    raise TypeError(f"no applicable method for 'augPred' applied to object of class {_show_classes(classes)}")


def comparePred(
    object1,
    object2,
    primary=_MISSING,
    minimum=_MISSING,
    maximum=_MISSING,
    length_out: int = 51,
    level=None,
    **kwargs,
) -> AugPredFrame:
    del kwargs
    if level is not None and len(_as_list(level)) > 1:
        raise ValueError("only one level allowed for predictions")
    caller = inspect.currentframe()
    try:
        call_frame = caller.f_back if caller is not None else None
        label1 = _deparsed_argument("object1", call_frame)
        label2 = _deparsed_argument("object2", call_frame)
    finally:
        del caller
    args = {
        "primary": primary,
        "level": level,
        "length_out": length_out,
    }
    if primary is not _MISSING and primary is not None:
        args["minimum"] = minimum
        args["maximum"] = maximum
    val1 = augPred(object1, **args)
    val2 = augPred(object2, **args)
    return _combine_compare(val1, val2, label1, label2)


def _aug_pred_lme(
    object: LmeFit,
    *,
    primary,
    minimum,
    maximum,
    length_out: int,
    level,
) -> AugPredFrame:
    data = _eval_parent_data(object)
    primary_values, pr_name, pr_var_text, resp_name = _resolve_primary(object, data, primary)
    if minimum is _MISSING:
        minimum = float(np.min(primary_values))
    if maximum is _MISSING:
        maximum = float(np.max(primary_values))
    new_primary = np.linspace(minimum, maximum, length_out, dtype=np.float64)
    q = object.dims.Q
    if level is _MISSING or level is None:
        level = q
    levels = _as_list(level)
    n_level = len(levels)
    max_lev = max([*levels, 1])
    groups = get_groups_lme(object, level=max_lev)
    groups = np.asarray(groups, dtype=np.object_)
    group_levels = object.group_level_labels
    unique_groups = list(dict.fromkeys(str(item) for item in groups))
    gr_name = ".groups"
    grid_primary = np.tile(np.tile(new_primary, len(unique_groups)), n_level)
    grid_groups = np.tile(np.repeat(unique_groups, len(new_primary)), n_level)
    value = {
        pr_name: grid_primary.tolist(),
        gr_name: grid_groups,
    }
    summ, summ_rows = gsummary(_as_column_dict(data), groups=groups)
    value.update(_expand_summary(summ, summ_rows, value[gr_name], skip=set(value)))
    predict_rows = len(grid_primary) // n_level
    predict_frame = {key: values[:predict_rows] for key, values in value.items()}
    pred = predict_lme(object, predict_frame, level=levels if n_level == 1 else levels)
    if n_level > 1:
        raise NotImplementedError("multiple augPred levels not implemented")
    pred_names = np.repeat("predicted", len(grid_primary))
    newvals = {
        pr_name: value[pr_name],
        gr_name: value[gr_name],
        resp_name: np.asarray(pred, dtype=np.float64),
    }
    orig = {
        pr_name: primary_values,
        gr_name: np.asarray([str(item) for item in groups], dtype=np.object_),
        resp_name: get_response_lme(object),
    }
    columns = {
        pr_name: np.concatenate([orig[pr_name], newvals[pr_name]]),
        gr_name: np.concatenate([orig[gr_name], newvals[gr_name]]),
        resp_name: np.concatenate([orig[resp_name], newvals[resp_name]]),
    }
    type_levels = ("predicted", "original")
    type_column = np.array(
        ["original"] * len(primary_values) + list(pred_names),
        dtype=np.object_,
    )
    columns[".type"] = type_column
    labels, units = _labels_units(data, pr_name, resp_name)
    formula = f"{resp_name} ~ {pr_name} | {gr_name}"
    return AugPredFrame(
        columns=columns,
        column_names=(pr_name, gr_name, resp_name, ".type"),
        type_levels=type_levels,
        labels=labels,
        units=units,
        formula=formula,
        group_levels=group_levels,
    )


def _aug_pred_lm_list(
    object: LmListFit,
    *,
    primary,
    minimum,
    maximum,
    length_out: int,
) -> AugPredFrame:
    data = _eval_parent_data(object)
    primary_values, pr_name, _pr_var, resp_name = _resolve_primary(object, data, primary)
    if minimum is _MISSING:
        minimum = float(np.min(primary_values))
    if maximum is _MISSING:
        maximum = float(np.max(primary_values))
    new_primary = np.linspace(minimum, maximum, length_out, dtype=np.float64)
    groups = get_groups_lm_list(object)
    unique_groups = list(dict.fromkeys(str(item) for item in groups))
    gr_name = _group_var_name(object)
    value = {
        pr_name: np.tile(new_primary, len(unique_groups)).tolist(),
        gr_name: np.repeat(unique_groups, len(new_primary)).tolist(),
    }
    summ, summ_rows = gsummary(_as_column_dict(data), groups=groups)
    value.update(_expand_summary(summ, summ_rows, value[gr_name], skip=set(value)))
    pred = predict_lm_list(object, value)
    newvals = {
        pr_name: np.asarray(value[pr_name], dtype=np.float64),
        gr_name: np.asarray(value[gr_name], dtype=np.object_),
        resp_name: np.asarray(pred, dtype=np.float64),
    }
    orig = {
        pr_name: primary_values,
        gr_name: np.asarray(groups, dtype=np.object_),
        resp_name: get_response_lm_list(object),
    }
    columns = {
        pr_name: np.concatenate([orig[pr_name], newvals[pr_name]]),
        gr_name: np.concatenate([orig[gr_name], newvals[gr_name]]),
        resp_name: np.concatenate([orig[resp_name], newvals[resp_name]]),
    }
    type_levels = ("predicted", "original")
    type_column = np.array(
        ["original"] * len(primary_values) + ["predicted"] * len(newvals[pr_name]),
        dtype=np.object_,
    )
    columns[".type"] = type_column
    labels, units = _labels_units(data, pr_name, resp_name)
    formula = f"{resp_name} ~ {pr_name} | {gr_name}"
    group_levels = _group_level_labels(data, object, groups)
    return AugPredFrame(
        columns=columns,
        column_names=(pr_name, gr_name, resp_name, ".type"),
        type_levels=type_levels,
        labels=labels,
        units=units,
        formula=formula,
        classes=("augPred", "data.frame"),
        group_levels=group_levels,
    )


def _group_level_labels(data, object, groups) -> tuple[str, ...]:
    levels = getattr(data, "group_levels", None)
    if levels:
        return tuple(str(item) for item in levels)
    if hasattr(object, "group_level_labels"):
        return tuple(object.group_level_labels)
    return tuple(dict.fromkeys(str(item) for item in groups))


def _combine_compare(val1: AugPredFrame, val2: AugPredFrame, c1: str, c2: str) -> AugPredFrame:
    val2 = _align_compare_names(val1, val2)
    n1 = len(val1.columns[val1.column_names[0]])
    n2 = len(val2.columns[val2.column_names[0]])
    gr1 = val1.column_names[1]
    gr2 = val2.column_names[1]
    type1 = _relabel_type(val1.columns[".type"], "predicted", c1)
    type2_all = _relabel_type(val2.columns[".type"], "predicted", c2)
    type2 = type2_all[np.array([str(item) != "original" for item in type2_all], dtype=bool)]
    mask2 = np.array([str(item) != "original" for item in val2.columns[".type"]], dtype=bool)
    if n1 == n2:
        lv1 = sorted(set(str(item) for item in val1.columns[gr1]))
        lv2 = sorted(set(str(item) for item in val2.columns[gr2]))
        if len(lv1) != len(lv2) or lv1 != lv2:
            raise ValueError(f"{c1} and {c2} must have the same group levels")
        cols = val1.column_names[:3]
        merged = {
            cols[0]: np.concatenate([val1.columns[cols[0]], val2.columns[cols[0]][mask2]]),
            cols[1]: np.concatenate([val1.columns[cols[1]], val2.columns[cols[1]][mask2]]),
            cols[2]: np.concatenate([val1.columns[cols[2]], val2.columns[cols[2]][mask2]]),
        }
        merged[".type"] = np.concatenate([type1, type2])
        formula = val1.formula
    elif n1 > n2:
        mult = n1 // n2
        if len(set(str(item) for item in val2.columns[gr2])) != 1 or len(set(str(item) for item in val1.columns[gr1])) != mult:
            raise ValueError("wrong group levels")
        cols = val1.column_names[:3]
        merged = {
            cols[0]: np.concatenate([val1.columns[cols[0]], np.tile(val2.columns[cols[0]], mult)]),
            cols[1]: np.concatenate([val1.columns[cols[1]], np.repeat(val1.columns[cols[1]], 2)]),
            cols[2]: np.concatenate([val1.columns[cols[2]], np.tile(val2.columns[cols[2]], mult)]),
        }
        merged[".type"] = np.concatenate([type1, np.tile(type2, mult)])
        formula = val1.formula
    else:
        mult = n2 // n1
        if len(set(str(item) for item in val1.columns[gr1])) != 1 or len(set(str(item) for item in val2.columns[gr2])) != mult:
            raise ValueError("wrong group levels")
        cols = val2.column_names[:3]
        merged = {
            cols[0]: np.concatenate([np.tile(val1.columns[cols[0]], mult), val2.columns[cols[0]]]),
            cols[1]: np.concatenate([np.repeat(val2.columns[cols[1]], 2), val2.columns[cols[1]]]),
            cols[2]: np.concatenate([np.tile(val1.columns[cols[2]], mult), val2.columns[cols[2]]]),
        }
        merged[".type"] = np.concatenate([np.tile(type1, mult), type2_all])
        formula = val2.formula
    type_levels = (c1, c2, "original")
    names = val1.column_names
    return AugPredFrame(
        columns=merged,
        column_names=(*names[:3], ".type"),
        type_levels=type_levels,
        labels=val1.labels,
        units=val1.units,
        formula=formula,
        classes=("comparePred", "augPred", "data.frame"),
        group_levels=val1.group_levels,
    )


def _resolve_primary(object, data, primary):
    if primary is _MISSING or primary is None:
        if not _is_grouped_data(data):
            raise ValueError("augPred without primary requires groupedData")
        formula = getattr(data, "formula", None) or getattr(object, "formula", None)
        if formula is None:
            raise ValueError("missing formula on grouped data")
        primary_values = get_covariate_data_frame(formula, _as_column_dict(data))
        pr_var = getCovariateFormula(formula)
        pr_name = pr_var.text.lstrip("~").strip()
    else:
        pr_var = getCovariateFormula(primary)
        pr_name = pr_var.text.lstrip("~").strip()
        primary_values = get_covariate_data_frame(primary, _as_column_dict(data))
    resp = getResponseFormula(getattr(object, "formula", formula if primary is _MISSING or primary is None else primary))
    resp_name = resp.text.lstrip("~").strip()
    return np.asarray(primary_values, dtype=np.float64), pr_name, pr_var.text, resp_name


def _eval_parent_data(object):
    call = getattr(object, "call", None)
    if call is None:
        raise ValueError("fitted object missing call$data")
    data = call.data
    if not isinstance(data, dict) and not hasattr(data, "columns"):
        raise TypeError("data must be a data frame")
    return data


def _as_column_dict(data) -> dict[str, list[Any]]:
    if isinstance(data, dict):
        return {key: list(values) for key, values in data.items()}
    if hasattr(data, "columns"):
        columns = data.columns
        if isinstance(columns, dict):
            return {key: list(np.asarray(values).ravel()) for key, values in columns.items()}
    raise TypeError("data must expose columns")


def _labels_units(data, pr_name: str, resp_name: str) -> tuple[dict[str, str], dict[str, str]]:
    labels = {"x": pr_name, "y": resp_name}
    units = {"x": "", "y": ""}
    if _is_grouped_data(data):
        data_labels = getattr(data, "labels", None) or {}
        data_units = getattr(data, "units", None) or {}
        for key, value in data_labels.items():
            labels[key] = value
        for key, value in data_units.items():
            units[key] = value
    return labels, units


def _group_var_name(object: LmListFit) -> str:
    side = object.groups_form
    if isinstance(side, str):
        return side.lstrip("~").strip()
    return "Subject"


def _is_grouped_data(data) -> bool:
    classes = getattr(data, "classes", None)
    if classes and "groupedData" in classes:
        return True
    return hasattr(data, "formula") and hasattr(data, "labels")


def _class_vector(object) -> list[str]:
    classes = getattr(object, "classes", None)
    if classes:
        return list(classes)
    return []


def _show_classes(classes: Sequence[str]) -> str:
    quoted = ", ".join(f'"{name}"' for name in classes)
    return f"c({quoted})"


def _as_list(value) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _deparsed_argument(name: str, caller: FrameType | None) -> str:
    if caller is None:
        return name
    if name in caller.f_locals:
        return name
    return name


def _align_compare_names(val1: AugPredFrame, val2: AugPredFrame) -> AugPredFrame:
    if val1.column_names == val2.column_names:
        return val2
    renamed = {
        val1.column_names[index]: val2.columns[val2.column_names[index]]
        for index in range(len(val1.column_names))
    }
    return AugPredFrame(
        columns=renamed,
        column_names=val1.column_names,
        type_levels=val2.type_levels,
        labels=val2.labels,
        units=val2.units,
        formula=val2.formula,
        classes=val2.classes,
        group_levels=val1.group_levels,
    )


def _expand_summary(
    summ: dict[str, list[Any]],
    summ_rows: tuple[str, ...],
    group_column: list[Any],
    *,
    skip: set[str] | None = None,
) -> dict[str, list[Any]]:
    if not summ:
        return {}
    skip = skip or set()
    row_index = {name: index for index, name in enumerate(summ_rows)}
    out: dict[str, list[Any]] = {}
    for column, values in summ.items():
        if column in skip:
            continue
        out[column] = [values[row_index[str(group)]] for group in group_column]
    return out


def _relabel_type(values: np.ndarray, old: str, new: str) -> np.ndarray:
    return np.array([new if str(item) == old else str(item) for item in values], dtype=np.object_)


def _factor_codes(values: np.ndarray, levels: tuple[str, ...] | None) -> np.ndarray:
    if levels is None:
        levels = tuple(dict.fromkeys(str(item) for item in values))
    index = {level: code for code, level in enumerate(levels, start=1)}
    return np.asarray([index.get(str(item), np.nan) for item in values], dtype=np.float64)


def _ordered_codes(values: np.ndarray, levels: tuple[str, ...]) -> np.ndarray:
    index = {level: code for code, level in enumerate(levels, start=1)}
    return np.asarray([index.get(str(item), np.nan) for item in values], dtype=np.float64)
