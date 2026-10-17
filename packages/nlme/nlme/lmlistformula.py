"""List of ``lm`` fits by group (nlme ``lmList.formula``)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme.astable import GroupedData
from nlme.comparefits import NamedMatrix
from nlme.getcovariateformula import getCovariateFormula
from nlme.linpack_qr import dqrdc2, dqrsl

_MISSING = object()


@dataclass(slots=True)
class LmFit:
    """Minimal ``lm`` result for ``lmList``."""

    coefficients: dict[str, float]
    rss: float
    n_resid: int
    residuals: np.ndarray | None = None


@dataclass(slots=True)
class LmList:
    """List of per-group ``lm`` fits with ``lmList`` metadata."""

    entries: tuple[tuple[str, LmFit | BaseException], ...]
    level: int
    pool: bool
    groups_form: str
    group_names: tuple[str, ...]
    labels: dict[str, str] | None = None
    units: dict[str, str] | None = None

    def __iter__(self):
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)


def lmList_formula(
    object,
    data,
    level=_MISSING,
    subset=_MISSING,
    na_action=_MISSING,
    pool: bool = True,
    warn_lm: bool = True,
) -> LmList:
    """Fit ``lm`` separately for each level of the grouping factor in ``object``."""
    formula = _formula_text(object)
    frame = _as_data_frame(data)
    if subset is not _MISSING:
        raise NotImplementedError("subset is not implemented for lmList.formula")
    if na_action is _MISSING:
        na_action = na_fail
    frame = na_action(frame)
    grp_form = _get_groups_formula(formula, as_list=False)
    if grp_form is None:
        if _is_grouped_data(data):
            raise NotImplementedError("lmList.formula without groups in formula needs groupedData")
        raise ValueError(
            "'data' must be a \"groupedData\" object if 'groups' argument is missing"
        )
    grp_list = _get_groups_formula(formula, as_list=True)
    if level is _MISSING:
        level = len(grp_list)
    elif _length(level) > 1:
        raise ValueError("multiple levels not allowed")
    group_var = grp_list[level - 1].lstrip("~").strip()
    groups = _get_groups(frame, group_var, data)
    cov_side = getCovariateFormula(formula).text.lstrip("~").strip()
    response = formula.split("~", 1)[0].strip()
    model = f"{response} ~ {cov_side}"
    present = {str(value) for value in frame[group_var]}
    group_levels = tuple(
        level_name for level_name in _group_level_order(data, frame[group_var]) if level_name in present
    )
    val: list[tuple[str, LmFit | BaseException]] = []
    for name in group_levels:
        rows = [index for index, group in enumerate(groups) if group == name]
        part = {column: [values[index] for index in rows] for column, values in frame.items()}
        try:
            fit = _lm(model, part)
        except Exception as exc:
            fit = exc
        val.append((name, fit))
    val = _warn_err_list(val, warn=warn_lm)
    labels = getattr(data, "labels", None)
    units = getattr(data, "units", None)
    if _is_grouped_data(data) and labels is None and units is None:
        labels = getattr(data, "labels", None)
        units = getattr(data, "units", None)
    return LmList(
        entries=tuple(val),
        level=int(level),
        pool=bool(pool),
        groups_form=grp_form,
        group_names=tuple(name for name, _ in val),
        labels=labels,
        units=units,
    )


def coef(object: LmList, aug_frame: bool = False, **_ignored) -> NamedMatrix | None:
    """Extract coefficients from an ``lmList`` object as a named matrix."""
    del _ignored
    if aug_frame:
        raise NotImplementedError("augFrame is not implemented for coef.lmList")
    coefs = []
    for _name, entry in object.entries:
        if isinstance(entry, BaseException):
            coefs.append(None)
        else:
            coefs.append(entry.coefficients)
    non_null = [item is not None for item in coefs]
    if not any(non_null):
        return None
    coef_names: list[str] = []
    for item in coefs:
        if item is None:
            continue
        for name in item:
            if name not in coef_names:
                coef_names.append(name)
    matrix = np.full((len(coefs), len(coef_names)), np.nan, dtype=np.float64)
    row_names = object.group_names
    for row, item in enumerate(coefs):
        if item is None:
            continue
        for col, name in enumerate(coef_names):
            if name in item:
                matrix[row, col] = item[name]
    return NamedMatrix(matrix, row_names, tuple(coef_names))


def na_fail(frame: dict[str, list[Any]]) -> dict[str, list[Any]]:
    """Default ``na.action`` for ``lmList``: fail on any missing value."""
    for column, values in frame.items():
        for value in values:
            if value is None:
                raise ValueError("missing values in object")
            if isinstance(value, float) and np.isnan(value):
                raise ValueError("missing values in object")
    return frame


def _lm(formula: str, data: dict[str, list[Any]]) -> LmFit:
    response, rhs = formula.split("~", 1)
    response = response.strip()
    terms = [term.strip() for term in rhs.split("+")]
    rows = len(data[response])
    y = np.asarray(data[response], dtype=np.float64)
    columns = [np.ones(rows, dtype=np.float64)]
    names = ["(Intercept)"]
    for term in terms:
        if not term:
            continue
        columns.append(np.asarray(data[term], dtype=np.float64))
        names.append(term)
    design = np.column_stack(columns)
    if np.any(np.isnan(design)) or np.any(np.isnan(y)):
        raise ValueError("0 (non-NA) cases")
    # lm.fit: dqrls, that is dqrdc2 with tol 1e-7, then dqrsl with job 1110.
    mat = np.array(design, dtype=np.float64, order="F", copy=True)
    rank, qraux, _pivot = dqrdc2(mat, 1e-7)
    if rank < design.shape[1]:
        raise ValueError("singular fit")
    solved = dqrsl(mat, rank, qraux, y, 1110)
    coef = np.asarray(solved["b"], dtype=np.float64)[: design.shape[1]]
    resid = np.asarray(solved["rsd"], dtype=np.float64)
    coefficients = {name: float(value) for name, value in zip(names, coef, strict=True)}
    return LmFit(
        coefficients=coefficients,
        rss=float(np.dot(resid, resid)),
        n_resid=rows,
        residuals=resid,
    )


def _formula_text(object) -> str:
    if isinstance(object, str) and "~" in object:
        return object.strip()
    if hasattr(object, "formula"):
        value = object.formula
        if isinstance(value, str) and "~" in value:
            return value.strip()
    raise ValueError("object must be a two-sided formula")


def _as_data_frame(data) -> dict[str, list[Any]]:
    if isinstance(data, GroupedData):
        raise TypeError("groupedData for lmList.formula must expose columns or use a data frame dict")
    if hasattr(data, "columns") and isinstance(data.columns, dict):
        return {key: list(values) for key, values in data.columns.items()}
    if isinstance(data, dict):
        return {key: list(values) for key, values in data.items()}
    raise TypeError("data must be a data frame")


def _is_grouped_data(data) -> bool:
    classes = getattr(data, "classes", None)
    if classes and "groupedData" in classes:
        return True
    return isinstance(data, GroupedData)


def _get_groups_formula(formula: str, *, as_list: bool) -> str | list[str] | None:
    if "|" not in formula.split("~", 1)[1]:
        return None
    rhs = formula.split("~", 1)[1]
    group_side = _bar_rhs(rhs)
    one_sided = f"~{group_side.strip()}"
    if not as_list:
        return one_sided
    return [one_sided]


def _bar_rhs(rhs: str) -> str:
    depth = 0
    start = 0
    for index, char in enumerate(rhs):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "|" and depth == 0:
            start = index + 1
    return rhs[start:].strip()


def _get_groups(
    frame: dict[str, list[Any]],
    group_var: str,
    data,
) -> list[str]:
    return [str(item) for item in frame[group_var]]


def _group_level_order(data, values) -> tuple[str, ...]:
    levels = getattr(data, "group_levels", None)
    if levels:
        return tuple(str(level) for level in levels)
    seen: list[str] = []
    for value in values:
        text = str(value)
        if text not in seen:
            seen.append(text)
    return tuple(seen)


def _length(value) -> int:
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _warn_err_list(
    val: list[tuple[str, LmFit | BaseException]],
    *,
    warn: bool,
) -> list[tuple[str, LmFit | BaseException]]:
    errs = [index for index, (_name, item) in enumerate(val) if isinstance(item, BaseException)]
    if not errs:
        return val
    if warn:
        warnings.warn(
            f"{len(errs)} lm fit(s) errored; see lmList element(s) {errs}",
            UserWarning,
            stacklevel=3,
        )
    return val
