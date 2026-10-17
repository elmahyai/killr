"""Extract the response vector from a model or formula (nlme ``getResponse``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme.balancedgrouped import BalancedGroupedData
from nlme.getresponseformula import getResponseFormula


@dataclass(frozen=True, slots=True)
class ResponseVector:
    """Numeric response with optional ``label`` attribute."""

    values: np.ndarray
    label: str | None = None

    def __array__(self, dtype=None, copy=None):
        if dtype is None:
            dtype = np.float64
        return np.asarray(self.values, dtype=dtype, copy=copy)


@dataclass(slots=True)
class Lme:
    """``lme`` stand-in for ``getResponse.lme``."""

    fitted: np.ndarray
    resid: np.ndarray
    labels: dict[str, str] | None = None
    units: dict[str, str] | None = None
    formula: str | None = None
    classes: tuple[str, ...] = ("lme",)


@dataclass(slots=True)
class Gls:
    """``gls`` stand-in for ``getResponse.gls``."""

    fitted: np.ndarray
    resid: np.ndarray
    labels: dict[str, str] | None = None
    units: dict[str, str] | None = None
    formula: str | None = None
    classes: tuple[str, ...] = ("gls",)


@dataclass(slots=True)
class LmList:
    """``lmList`` stand-in for ``getResponse.lmList``."""

    fitted: np.ndarray
    resid: np.ndarray
    classes: tuple[str, ...] = ("lmList",)


@dataclass(slots=True)
class GroupedDataFrame:
    """``data.frame`` stand-in for ``getResponse.data.frame``."""

    columns: dict[str, np.ndarray]
    formula: str | None = None
    classes: tuple[str, ...] = ("data.frame",)


def getResponse(object, form=None):
    """Extract the response vector from ``object``."""
    classes = _class_vector(object)
    if "lme" in classes:
        return _get_response_lme_gls(object)
    if "gls" in classes:
        return _get_response_lme_gls(object)
    if "lmList" in classes:
        return _get_response_lmlist(object)
    if isinstance(object, BalancedGroupedData) or "data.frame" in classes:
        if form is None:
            form = _default_formula(object)
        return _get_response_data_frame(object, form)
    shown = _show_classes(classes)
    raise TypeError(f"no applicable method for 'getResponse' applied to an object of class {shown}")


def _get_response_lme_gls(obj: Lme | Gls) -> ResponseVector:
    fitted = np.asarray(obj.fitted, dtype=np.float64)
    resid = np.asarray(obj.resid, dtype=np.float64)
    values = resid + fitted
    label = None
    if obj.labels is not None:
        label = obj.labels.get("y")
    if label is None and obj.formula is not None:
        label = _response_term(getResponseFormula(obj))
    if label is not None and obj.units is not None and (unit := obj.units.get("y")):
        label = f"{label} {unit}"
    return ResponseVector(values, label=label)


def _get_response_lmlist(obj: LmList) -> np.ndarray:
    fitted = np.asarray(obj.fitted, dtype=np.float64)
    resid = np.asarray(obj.resid, dtype=np.float64)
    return fitted + resid


def _get_response_data_frame(object, form) -> np.ndarray:
    text = _formula_text(form)
    if text is None or "~" not in text:
        raise ValueError("'form' must be a two-sided formula")
    lhs = text.split("~", 1)[0].strip()
    if not lhs:
        raise ValueError("'form' must be a two-sided formula")
    columns = _columns(object)
    if lhs not in columns:
        raise KeyError(lhs)
    return np.asarray(columns[lhs], dtype=np.float64)


def _response_term(formula) -> str:
    text = str(formula).strip()
    if text.startswith("~"):
        return text[1:].strip()
    return text


def _default_formula(object) -> str:
    if hasattr(object, "formula") and object.formula:
        return str(object.formula).strip()
    raise ValueError("formula(object) must return a formula")


def _formula_text(form) -> str | None:
    if isinstance(form, str) and "~" in form:
        return form.strip()
    if hasattr(form, "formula"):
        value = form.formula
        if isinstance(value, str) and "~" in value:
            return value.strip()
    return None


def _columns(object) -> dict[str, np.ndarray]:
    if isinstance(object, BalancedGroupedData):
        return object.columns
    columns = getattr(object, "columns", None)
    if isinstance(columns, dict):
        return columns
    raise TypeError("expected data frame stand-in")


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
