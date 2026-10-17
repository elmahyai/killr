"""Extract model data from fitted objects (nlme ``getData``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np


@dataclass(slots=True)
class ModelFrame:
    """Tabular model data with optional groupedData-style attributes."""

    columns: dict[str, np.ndarray]
    formula: str | None = None
    labels: dict[str, str] | None = None
    units: dict[str, str] | None = None
    classes: tuple[str, ...] = ("data.frame",)

    @property
    def nrow(self) -> int:
        first = next(iter(self.columns.values()))
        return int(len(first))


@dataclass(slots=True)
class LmeCall:
    """``call`` slice used by ``getData.lme``."""

    data: Any | None = None
    subset: Any | None = None
    na_action: Any | None = None


@dataclass(slots=True)
class Lme:
    """``lme`` / ``nls`` stand-in for ``getData``."""

    data: ModelFrame | Mapping[str, np.ndarray] | None = None
    call: LmeCall | None = None
    na_action: Any | None = None
    classes: tuple[str, ...] = ("lme",)


@dataclass(slots=True)
class LmList:
    """``lmList`` stand-in for ``getData.lmList``."""

    data: ModelFrame | Mapping[str, np.ndarray] | None
    call: LmeCall
    classes: tuple[str, ...] = ("lmList",)


@dataclass(slots=True)
class Gnls:
    """``gnls`` / ``nlme`` stand-in for ``getData``."""

    call: LmeCall
    classes: tuple[str, ...] = ("gnls",)


@dataclass(slots=True)
class Gls:
    """``gls`` stand-in for ``getData.gls``."""

    data: ModelFrame | Mapping[str, np.ndarray] | None = None
    call: LmeCall | None = None
    na_action: Any | None = None
    classes: tuple[str, ...] = ("gls",)


def getData(object):
    """Return the data used to fit ``object``."""
    classes = _class_vector(object)
    if "lme" in classes or "nls" in classes:
        return _get_data_lme_nls(object)
    if "gls" in classes:
        return _get_data_gls(object)
    if "lmList" in classes:
        return _get_data_lmlist(object)
    if "gnls" in classes:
        return _get_data_gnls(object)
    if "nlme" in classes:
        return _get_data_nlme(object)
    shown = _show_classes(classes)
    raise TypeError(f"no applicable method for 'getData' applied to an object of class {shown}")


def _get_data_lme_nls(obj: Lme):
    call = obj.call or LmeCall()
    if obj.data is not None:
        data = _as_frame(obj.data)
    elif call.data is not None:
        data = _as_frame(call.data)
    else:
        return None
    data = _apply_na_action(data, obj.na_action, call.na_action)
    data = _apply_subset(data, call.subset)
    return data


def _get_data_gls(obj: Gls):
    return _get_data_lme_nls(
        Lme(data=obj.data, call=obj.call, na_action=obj.na_action, classes=obj.classes)
    )


def _get_data_lmlist(obj: LmList):
    data = _as_frame(obj.call.data) if obj.call.data is not None else None
    if data is None:
        return None
    na_act = obj.call.na_action
    if na_act is not None and callable(na_act):
        data = na_act(data)
    data = _apply_subset(data, obj.call.subset)
    return data


def _get_data_gnls(obj: Gnls):
    data = _as_frame(obj.call.data) if obj.call.data is not None else None
    if data is None:
        return None
    na_pat = obj.call.na_action
    if na_pat is not None and callable(na_pat):
        data = na_pat(data)
    na_act = getattr(obj.call, "na_action_fn", None)
    if na_act is not None and callable(na_act):
        data = na_act(data)
    data = _apply_subset(data, obj.call.subset)
    return data


def _get_data_nlme(obj: Gnls):
    return _get_data_gnls(obj)


def _as_frame(data: ModelFrame | Mapping[str, np.ndarray]) -> ModelFrame:
    if isinstance(data, ModelFrame):
        return ModelFrame(
            {key: np.asarray(values) for key, values in data.columns.items()},
            formula=data.formula,
            labels=data.labels,
            units=data.units,
            classes=data.classes,
        )
    return ModelFrame({key: np.asarray(values) for key, values in data.items()})


def _apply_na_action(
    data: ModelFrame,
    object_na: Any,
    call_na: Any,
) -> ModelFrame:
    na_act = object_na if object_na is not None else call_na
    if na_act is None:
        return data
    if isinstance(na_act, str) and na_act == "omit":
        raise ValueError("na.action omit stand-in must be an index vector")
    if isinstance(na_act, (list, tuple, np.ndarray)):
        index = np.asarray(na_act, dtype=np.intp)
        return _subset_rows(data, ~np.isin(np.arange(data.nrow), index - 1))
    if hasattr(na_act, "kind"):
        kind = getattr(na_act, "kind")
        index = np.asarray(getattr(na_act, "index"), dtype=np.intp)
        if kind == "omit":
            return _subset_rows(data, ~np.isin(np.arange(data.nrow), index - 1))
        if kind == "exclude":
            return data
    if callable(na_act):
        return na_act(data)
    return data


def _apply_subset(data: ModelFrame, subset: Any) -> ModelFrame:
    if subset is None:
        return data
    if isinstance(subset, (list, tuple, np.ndarray)):
        mask = np.asarray(subset, dtype=bool)
        return _subset_rows(data, mask)
    if callable(subset):
        mask = np.asarray(subset(data), dtype=bool)
        return _subset_rows(data, mask)
    if isinstance(subset, str):
        mask = _eval_one_sided(subset, data)
        return _subset_rows(data, mask)
    raise TypeError("unsupported subset stand-in")


def _eval_one_sided(expr: str, data: ModelFrame) -> np.ndarray:
    text = expr.strip()
    if "==" in text:
        left, right = text.split("==", 1)
        col = left.strip()
        value = right.strip().strip("'").strip('"')
        column = np.asarray(data.columns[col], dtype=object)
        return column == value
    raise ValueError(f"unsupported subset expression {expr!r}")


def _subset_rows(data: ModelFrame, mask: np.ndarray) -> ModelFrame:
    mask = np.asarray(mask, dtype=bool)
    columns = {name: np.asarray(values)[mask] for name, values in data.columns.items()}
    return ModelFrame(columns, formula=data.formula, labels=data.labels, units=data.units, classes=data.classes)


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
