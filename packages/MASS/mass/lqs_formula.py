"""Formula interface for resistant regression (MASS lqs.formula)."""

from __future__ import annotations

from typing import Any

import numpy as np

from mass.addterm import _model_matrix
from mass.errors import MassError
from mass.lm_gls import _expand_dot_formula
from mass.lqs import LqsFit, lqs
from mass.rlm import _match_arg


def lqs_formula(
    formula: str,
    data: dict,
    *,
    method: str | None = None,
    subset: Any = None,
    na_action: Any = None,
    model: bool = True,
    x_ret: bool = False,
    y_ret: bool = False,
    contrasts: Any = None,
    **kwargs: Any,
) -> LqsFit | dict[str, Any]:
    """Fit resistant regression from a model formula."""
    method = _match_arg(method, ["lts", "lqs", "lms", "S", "model.frame"])
    if subset is not None or na_action is not None:
        raise MassError("subset and na.action are not implemented for lqs.formula")
    if contrasts is not None:
        raise MassError("contrasts are not implemented for lqs.formula")
    formula = _expand_dot_formula(formula, data)
    x_mat, y_vec, names, _labels = _model_matrix(data, formula)
    if method == "model.frame":
        return {"data": data, "formula": formula, "x": x_mat, "y": y_vec}
    xint = 1 if names and names[0] == "(Intercept)" else 0
    if xint:
        x_use = x_mat[:, 1:]
    else:
        x_use = x_mat
    fit = lqs(x_use, y_vec, intercept=xint > 0, method=method, **kwargs)
    fit.terms = formula
    fit.call = ("lqs", formula)
    fit.contrasts = contrasts
    fit.xlevels = None
    fit.na_action = None
    if model:
        fit.model = dict(data)
    if x_ret:
        fit.x = x_use
    if y_ret:
        fit.y = y_vec
    return fit
