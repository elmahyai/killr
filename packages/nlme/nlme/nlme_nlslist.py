"""``nlme.nlsList`` method (nlme ``nlme.nlsList``): fit ``nlme`` from an ``nlsList`` object.

R rebuilds the ``nlme`` call from the call stored on the ``nlsList`` object.
The model is the response and the nonlinear expression, the fixed parameters
start at the median of the group estimates, and the random-effects matrix
starts at the squared ratio of the median absolute deviations of the group
estimates and of the residuals. The fit itself is ``nlme.formula``.

Only ``SSasympOff`` models are translated, because ``nlsList.formula`` only
fits that model in this package.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from nlme.lme_family import NlmeResult, _formula_text, _mad, nlme_formula
from nlme.nlslistformula import (
    NlsFit,
    NlsList,
    _as_data_frame,
    _covariate_formula,
    _get_groups,
    _parse_ss_asymp_off,
    _ss_asymp_off,
)

__all__ = ["nlme_nlsList", "random_start_matrix"]


def _random_names(random: Any) -> tuple[str, ...]:
    """Left-hand side names of a one-sided ``random`` formula, like ``rnames``."""
    text = _formula_text(random)
    lhs = text.split("~", 1)[0]
    return tuple(part.strip() for part in lhs.split("+") if part.strip())


def _group_rows(frame: dict[str, list[Any]], group_var: str, names: list[str]) -> dict[str, list[int]]:
    groups = _get_groups(frame, group_var)
    rows: dict[str, list[int]] = {name: [] for name in names}
    for index, group in enumerate(groups):
        if group in rows:
            rows[group].append(index)
    return rows


def random_start_matrix(
    model: NlsList,
    data: Any,
    random_names: tuple[str, ...],
    group_var: str,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return ``(coefficients, mad_ratio, param_names)`` for the nlsList starting values.

    ``mad_ratio`` is ``(madRan / madRes)^2`` for each random name, the diagonal
    of the starting ``reStruct`` matrix in ``nlme.nlsList``.
    """
    response, covariate, param_names = _parse_ss_asymp_off(_covariate_formula(model.formula))
    frame = _as_data_frame(data)
    # na.omit(coef(model)): groups whose fit failed are dropped.
    fitted = [(name, fit) for name, fit in model.entries if isinstance(fit, NlsFit)]
    coef_rows = np.array(
        [[fit.coefficients[p] for p in param_names] for _name, fit in fitted], dtype=np.float64
    )
    coef_rows = coef_rows.reshape(len(fitted), len(param_names))
    # residuals of the successful group fits, as resid(model)
    rows = _group_rows(frame, group_var, [name for name, _fit in fitted])
    y = np.asarray(frame[response], dtype=np.float64)
    x = np.asarray(frame[covariate], dtype=np.float64)
    resid_parts = []
    for name, fit in fitted:
        index = np.asarray(rows[name], dtype=np.int64)
        beta = np.array([fit.coefficients[p] for p in param_names], dtype=np.float64)
        resid_parts.append(y[index] - _ss_asymp_off(x[index], beta))
    residuals = np.concatenate(resid_parts) if resid_parts else np.array([], dtype=np.float64)
    mad_res = _mad(residuals)
    mad_ran = np.array(
        [_mad(coef_rows[:, param_names.index(name)]) for name in random_names],
        dtype=np.float64,
    )
    return coef_rows, (mad_ran / mad_res) ** 2, list(param_names)


def nlme_nlsList(
    model: NlsList,
    data: Any = None,
    fixed: Any = None,
    random: Any = None,
    groups: Any = None,
    start: Any = None,
    correlation: Any = None,
    weights: Any = None,
    subset: Any = None,
    method: Any = "ML",
    na_action: Any = None,
    naPattern: Any = None,
    control: Any = None,
    verbose: bool = False,
) -> NlmeResult:
    """Fit ``nlme`` to the model stored on an ``nlsList`` object."""
    if not isinstance(model, NlsList):
        raise TypeError("nlme.nlsList needs an nlsList object")
    if model.formula is None:
        raise ValueError("nlsList object has no model formula")
    if correlation is not None or weights is not None or subset is not None:
        raise NotImplementedError("nlme.nlsList with correlation, weights, or subset is not translated")
    if fixed is not None:
        warnings.warn("'nlme.nlsList' will redefine 'fixed', 'data', and 'start'", stacklevel=2)
    if data is None:
        data = model.data
    if data is None:
        raise ValueError("'data' must be given explicitly to use 'nlsList'")
    method_text = method if isinstance(method, str) else "ML"
    if method_text not in {"ML", "REML"}:
        method_text = "ML"

    response, covariate, param_names = _parse_ss_asymp_off(_covariate_formula(model.formula))
    expression = f"SSasympOff({covariate}, {', '.join(param_names)})"
    group_form = groups if groups is not None else model.groups_form
    group_var = str(group_form).lstrip("~").strip()
    fixed_text = " + ".join(param_names) + " ~ 1"
    random_text = random if random is not None else fixed_text
    random_names = _random_names(random_text)

    coef_rows, _mad_ratio, _names = random_start_matrix(model, data, random_names, group_var)
    start_fixed = np.nanmedian(coef_rows, axis=0)

    return nlme_formula(
        f"{response} ~ {expression}",
        data,
        fixed_text,
        random=random_text,
        groups=group_form,
        start=start_fixed,
        method=method_text,
        control=control,
        verbose=verbose,
    )
