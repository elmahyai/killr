"""clm for ordinal 2026.7-26: cumulative link models from formulas.

Ports clm(), get_clmFormulas (the formula parts), get_clm.mf (model frame with
na.omit and drop.unused.levels), get_clmY and get_clmDesign. The fit goes
through clm_fit_core, which is the clm.fit.default port in clm_fit.py.

Data is a mapping from column name to a sequence of values. A column with any
string entry is a factor; its levels are sorted unless `levels` gives them.
Not yet ported: offset() terms, the flexible links, and the method options
other than Newton.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from ordinal.clm_fit import clm_fit_core
from ordinal.clm_frames import (
    _is_na,
    design_matrix,
    formula_variables,
    is_factor_values,
)


def _strip_tilde(formula: str) -> str:
    text = formula.strip()
    if text.startswith("~"):
        text = text[1:]
    return text.strip()


def _split_response(formula: str) -> tuple[str, str]:
    if "~" not in formula:
        raise ValueError("Model needs a formula with a response")
    lhs, rhs = formula.split("~", 1)
    return lhs.strip(), rhs.strip()


def clm(
    formula: str,
    data: Mapping[str, Sequence[Any]],
    *,
    scale: str | None = None,
    nominal: str | None = None,
    weights: Sequence[float] | None = None,
    levels: Mapping[str, Sequence[str]] | None = None,
    link: str = "logit",
    threshold: str = "flexible",
    start: np.ndarray | None = None,
    control: dict[str, Any] | None = None,
    do_fit: bool = True,
) -> dict[str, Any]:
    """clm(formula, scale, nominal, data, weights, start, link, threshold, control)."""
    if link in ("Aranda-Ordaz", "log-gamma"):
        raise NotImplementedError("flexible links need nlminb, which is not ported yet")
    resp, rhs = _split_response(formula)
    if "offset(" in rhs or (scale and "offset(" in scale) or (nominal and "offset(" in nominal):
        raise NotImplementedError("offset() terms are not ported yet")
    rhs = _strip_tilde(rhs)
    scale_rhs = _strip_tilde(scale) if scale else None
    nom_rhs = _strip_tilde(nominal) if nominal else None
    if nom_rhs is not None and "offset(" in nom_rhs:
        raise NotImplementedError("offset() terms are not ported yet")

    n = len(data[resp])
    keep = np.ones(n, dtype=bool)
    needed = [resp] + formula_variables(rhs)
    if scale_rhs is not None:
        needed += formula_variables(scale_rhs)
    if nom_rhs is not None:
        needed += formula_variables(nom_rhs)
    needed = list(dict.fromkeys(needed))
    for var in needed:
        keep &= np.array([not _is_na(v) for v in data[var]], dtype=bool)
    if weights is not None:
        w_all = np.asarray(weights, dtype=float)
        keep &= ~np.isnan(w_all)
        w = w_all[keep]
    else:
        w = np.ones(int(keep.sum()))
    sub = {var: [data[var][i] for i in range(n) if keep[i]] for var in needed}

    if not is_factor_values(sub[resp]):
        raise ValueError("response in 'formula' needs to be a factor")
    factor_vars = [v for v in needed if is_factor_values(sub[v]) or (levels and v in levels)]

    def present_levels(var: str, values: Sequence[Any]) -> list[str]:
        observed = {str(v) for v in values if not _is_na(v)}
        if levels and var in levels:
            base = [str(v) for v in levels[var]]
        else:
            base = sorted(observed)
        return [lev for lev in base if lev in observed]

    factor_levels = {v: present_levels(v, sub[v]) for v in factor_vars if v != resp}
    # y.levels are levels of y among rows with positive weight (get_clmY)
    y_positive = [sub[resp][i] for i in range(len(w)) if w[i] > 0]
    y_levels = present_levels(resp, y_positive)
    code_of = {lev: j + 1 for j, lev in enumerate(y_levels)}
    y_codes = np.array(
        [
            code_of.get(str(sub[resp][i]), 0) if w[i] > 0 else 0
            for i in range(len(w))
        ],
        dtype=int,
    )

    X, X_names = design_matrix(rhs, sub, factor_levels)
    S = S_names = None
    if scale_rhs is not None:
        S, S_names = design_matrix(scale_rhs, sub, factor_levels)
    N = N_names = None
    nom_info = None
    if nom_rhs is not None:
        N, N_names = design_matrix(nom_rhs, sub, factor_levels)
        nom_vars = formula_variables(nom_rhs)
        nom_info = {
            "rhs": nom_rhs,
            "factors": {v: factor_levels[v] for v in nom_vars if v in factor_levels},
            "numeric": any(v not in factor_levels for v in nom_vars),
        }

    return clm_fit_core(
        y_codes=y_codes,
        y_levels=y_levels,
        X=X,
        X_names=X_names,
        S=S,
        S_names=S_names,
        N=N,
        N_names=N_names,
        weights=w,
        offset=np.zeros(len(w)),
        S_offset=None,
        control=control,
        start=start,
        do_fit=do_fit,
        link=link,
        threshold=threshold,
        nom_info=nom_info,
    )
