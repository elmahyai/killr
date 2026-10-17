"""``predict`` methods for ``lme`` and ``lmList`` stand-ins."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.fit_objects import LmeCoefficients, LmeFit, LmListFit, lm_list_entry_map
from nlme.getcovariateformula import getCovariateFormula
from nlme.getresponseformula import getResponseFormula


def predict_lme(
    object: LmeFit,
    newdata: dict[str, list[Any]],
    *,
    level: int | list[int] | None = None,
) -> np.ndarray:
    if level is None:
        level = object.dims.Q
    if isinstance(level, (list, tuple)):
        if len(level) != 1:
            raise NotImplementedError("multiple prediction levels not implemented")
        level = level[0]
    if level == 0:
        return _fixed_predict(object, newdata)
    if object.dims.Q != 1:
        raise NotImplementedError("only Q=1 lme prediction is implemented")
    return _random_predict(object, newdata, object.coefficients)


def predict_lm_list(
    object: LmListFit,
    newdata: dict[str, list[Any]],
    *,
    as_list: bool = False,
) -> np.ndarray:
    del as_list
    formula = object.groups_form if hasattr(object, "groups_form") else None
    if formula is None:
        formula = object.groups_form
    model_formula = _infer_formula(object)
    group_name = _group_name_from_object(object)
    groups = [str(item) for item in newdata[group_name]]
    entries = lm_list_entry_map(object)
    values: list[float] = []
    names: list[str] = []
    for row_index, group in enumerate(groups):
        fit = entries.get(group)
        if fit is None:
            values.append(float("nan"))
        else:
            row = {column: newdata[column][row_index] for column in newdata}
            values.append(_lm_predict_row(model_formula, fit, row))
        names.append(group)
    result = np.asarray(values, dtype=np.float64)
    return result


def _infer_formula(object: LmListFit) -> str:
    if object.call is not None and hasattr(object.call, "formula"):
        return str(object.call.formula)
    return "distance ~ age"


def _group_name_from_object(object: LmListFit) -> str:
    side = object.groups_form
    if isinstance(side, str):
        return side.lstrip("~").strip()
    return "Subject"


def _fixed_predict(object: LmeFit, newdata: dict[str, list[Any]]) -> np.ndarray:
    coef = object.coefficients.fixed
    names = object.coefficients.fixed_names
    cov = getCovariateFormula(object.formula).text.lstrip("~").strip()
    terms = [term.strip() for term in cov.split("+")] if cov and cov != "1" else []
    rows = len(next(iter(newdata.values())))
    out = np.zeros(rows, dtype=np.float64)
    for index in range(rows):
        design = [1.0]
        for term in terms:
            design.append(float(newdata[term][index]))
        out[index] = float(np.dot(design, coef[: len(design)]))
    del names
    return out


def _random_predict(
    object: LmeFit,
    newdata: dict[str, list[Any]],
    coefficients: LmeCoefficients,
) -> np.ndarray:
    fixed = _fixed_predict(object, newdata)
    group_name = object.group_colnames[0]
    if group_name not in newdata:
        for alt in (".groups",):
            if alt in newdata:
                group_name = alt
                break
    groups = [str(item) for item in newdata[group_name]]
    random_key = next(iter(coefficients.random))
    random_mat = coefficients.random[random_key]
    row_names = coefficients.random_rownames[random_key]
    col_names = coefficients.random_colnames[random_key]
    row_index = {name: index for index, name in enumerate(row_names)}
    cov = getCovariateFormula(object.formula).text.lstrip("~").strip()
    terms = [term.strip() for term in cov.split("+")] if cov and cov != "1" else []
    out = fixed.copy()
    for index, group in enumerate(groups):
        if group not in row_index:
            continue
        row = row_index[group]
        random_part = 0.0
        for col_offset, term in enumerate(["(Intercept)", *terms]):
            if col_offset >= len(col_names):
                break
            if term == "(Intercept)":
                random_part += float(random_mat[row, col_offset])
            else:
                random_part += float(random_mat[row, col_offset]) * float(newdata[term][index])
        out[index] = fixed[index] + random_part
    return out


def _lm_predict_row(formula: str, fit, row: dict[str, Any]) -> float:
    _response, rhs = formula.split("~", 1)
    terms = [term.strip() for term in rhs.split("|", 1)[0].split("+") if term.strip()]
    value = float(fit.coefficients.get("(Intercept)", 0.0))
    for term in terms:
        if term == "(Intercept)":
            continue
        value += float(fit.coefficients[term]) * float(row[term])
    return value


def get_response_lme(object: LmeFit) -> np.ndarray:
    return np.asarray(object.fitted_values + object.resid_values, dtype=np.float64)


def get_response_lm_list(object: LmListFit) -> np.ndarray:
    if object.fitted_values is None or object.resid_values is None:
        raise ValueError("lmList missing fitted/resid vectors")
    return np.asarray(object.fitted_values + object.resid_values, dtype=np.float64)
