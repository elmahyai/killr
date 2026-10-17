"""Deprecated concordance wrapper (survival::survConcordance)."""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

from survival.strata import StrataFactor, strata as strata_fn
from survival.surv import Surv, SurvObject, is_Surv
from survival.surv_split import _apply_subset, _as_table, _column_len
from survival.survConcordance_fit import _concordance1, _concordance2
from survival.survobrien import _build_model_frame, _column_values, _drop_term
from survival.untangle_specials import untangle_specials
from survival._yates_mm import build_terms, model_matrix


def _legacy_btree(n: int) -> np.ndarray:
    """Tree ranks for survConcordance.fit (R btree in survConcordance.fit.R)."""
    if n < 1:
        return np.zeros(0, dtype=int)
    ranks = np.zeros(n, dtype=int)
    yet_to_do = list(range(1, n + 1))
    depth = int(math.floor(math.log(n, 2))) if n > 1 else 0
    start = int(2**depth)
    lastrow_length = 1 + n - start
    indx = list(range(0, lastrow_length * 2, 2))
    ranks[np.array(yet_to_do, dtype=int)[indx] - 1] = start + np.arange(len(indx), dtype=int)
    yet_to_do = [yet_to_do[i] for i in range(len(yet_to_do)) if i not in indx]
    while start > 1:
        start = start // 2
        indx = list(range(0, start * 2, 2))
        pick = [yet_to_do[i] for i in indx if i < len(yet_to_do)]
        ranks[np.array(pick, dtype=int) - 1] = start + np.arange(len(pick), dtype=int)
        yet_to_do = [yet_to_do[i] for i in range(len(yet_to_do)) if i not in indx]
    return ranks


def _docount_legacy(stime: np.ndarray, risk: np.ndarray, wts: np.ndarray, *, surv_type: str) -> np.ndarray:
    if surv_type == "right":
        ord_idx = np.lexsort((-stime[:, 1], stime[:, 0]))
        yord = stime[ord_idx]
        ux = np.sort(np.unique(risk))
        n2 = ux.size
        layout = _legacy_btree(n2)
        index = layout[np.searchsorted(ux, risk[ord_idx])] - 1
        return _concordance1(yord, wts[ord_idx], index.astype(int), n2)
    if surv_type == "counting":
        # order(-stop, status) and order(-start), as in survConcordance.fit
        sort_stop = np.lexsort((stime[:, 2], -stime[:, 1]))
        sort_start = np.argsort(-stime[:, 0], kind="stable")
        ux = np.sort(np.unique(risk))
        n2 = ux.size
        layout = _legacy_btree(n2)
        index = layout[np.searchsorted(ux, risk)] - 1
        return _concordance2(stime, wts, index.astype(int), n2, sort_stop, sort_start)
    raise ValueError("Invalid survival type for concordance")


def _surv_concordance_fit(
    y: SurvObject,
    x: np.ndarray,
    strata: Any | None = None,
    weight: np.ndarray | None = None,
) -> np.ndarray | np.ndarray:
    """Internal fitter matching survConcordance.fit (not exported)."""
    xarr = np.asarray(x, dtype=float).reshape(-1)
    if np.any(np.isnan(xarr)) or np.any(np.isnan(np.asarray(y.columns, dtype=float))):
        return None

    n = len(y)
    if weight is None or len(weight) == 0:
        wts = np.ones(n, dtype=float)
    else:
        wts = np.asarray(weight, dtype=float).reshape(-1)

    stime = np.asarray(y.columns, dtype=float)
    surv_type = y.type if y.type != "mright" else "right"
    if stime.shape[1] == 2:
        surv_type = "right"
    elif stime.shape[1] == 3:
        surv_type = "counting"

    if strata is None or len(strata) == 0:
        count = _docount_legacy(stime, xarr, wts, surv_type=surv_type)
        if count[0] == 0 and count[1] == 0:
            count[4] = 0.0
        else:
            count[4] = 2 * math.sqrt(count[4])
        return count

    if isinstance(strata, StrataFactor):
        strat_codes = np.array([1 if c is None else int(c) for c in strata.codes], dtype=int)
        level_labels = list(strata.levels)
        ustrat = [level_labels[i - 1] for i in range(1, len(level_labels) + 1) if np.any(strat_codes == i)]
        strat_vals = strat_codes
    else:
        strat_vals = np.asarray(strata)
        ustrat = list(np.unique(strat_vals))

    count = np.zeros((len(ustrat), 5), dtype=float)
    for i, level in enumerate(ustrat):
        if isinstance(strata, StrataFactor):
            keep = np.where(strat_vals == (level_labels.index(level) + 1))[0]
        else:
            keep = np.where(strat_vals == level)[0]
        yk = SurvObject(stime[keep], y.type, states=y.states, clabel=y.clabel)
        count[i, :] = _docount_legacy(
            np.asarray(yk.columns, dtype=float),
            xarr[keep],
            wts[keep],
            surv_type=surv_type,
        )
    zero_pairs = count[:, 0] + count[:, 1] == 0
    count[:, 4] = 2 * np.sqrt(np.where(zero_pairs, 0.0, count[:, 4]))
    return count


def _attach_weights_to_frame(
    mf_names: list[str],
    mf_cols: list[Any],
    weights: Any,
    data: Mapping[str, Any],
) -> tuple[list[str], list[Any]]:
    if weights is None:
        return mf_names, mf_cols
    if isinstance(weights, str):
        if weights not in data:
            raise ValueError(f"variable {weights!r} not found")
        wt_col = np.asarray(data[weights], dtype=float)
    else:
        wt_col = np.asarray(weights, dtype=float)
    if _column_len(wt_col) != _column_len(mf_cols[0]):
        raise ValueError("wrong length for weights")
    return mf_names + ["(weights)"], mf_cols + [wt_col]


def _model_matrix_predictor(Terms: dict[str, Any], mf_names: list[str], mf_cols: list[Any]) -> np.ndarray:
    lhs = mf_names[0]
    name_to_col = {name: col for name, col in zip(mf_names, mf_cols)}
    labels = Terms["term.labels"]
    if not labels:
        raise ValueError("Only one predictor variable allowed")
    table: dict[str, Any] = {}
    y_col = mf_cols[0]
    table[lhs] = y_col
    for label in labels:
        if label in name_to_col:
            col = name_to_col[label]
            if is_Surv(col):
                continue
            table[label] = _column_values(col)
        else:
            for name, col in name_to_col.items():
                if name == label:
                    table[label] = _column_values(col)
                    break
    new_formula = f"{lhs} ~ " + " + ".join(labels)
    terms_obj = build_terms(new_formula, table)
    mm_data = {lhs: y_col}
    for label in labels:
        mm_data[label] = table[label]
    xmat, _names, _assign = model_matrix(terms_obj, mm_data)
    if terms_obj.intercept and xmat.shape[1] > 0:
        xmat = xmat[:, 1:]
    if xmat.shape[1] > 1:
        raise ValueError("Only one predictor variable allowed")
    if xmat.shape[1] == 0:
        raise ValueError("Only one predictor variable allowed")
    return xmat[:, 0]


def survConcordance(
    formula,
    data=None,
    weights=None,
    subset=None,
    na_action=None,
):
    """Deprecated concordance wrapper using the legacy survConcordance.fit kernel."""
    if data is None and isinstance(formula, str):
        raise ValueError("a data argument is required")
    formula_text = str(formula)
    call = ("survConcordance", formula, data, weights, subset, na_action)

    table = _as_table(data)
    table, _ = _apply_subset(table, subset)
    mf_names, mf_cols, Terms = _build_model_frame(
        formula_text,
        table,
        subset=None,
        na_action=na_action,
    )
    mf_names, mf_cols = _attach_weights_to_frame(mf_names, mf_cols, weights, table)

    Y = mf_cols[0]
    if not is_Surv(Y):
        flat = np.asarray(Y, dtype=float).reshape(-1)
        if flat.ndim == 1 and flat.size == _column_len(mf_cols[0]):
            Y = Surv(flat)
        else:
            raise ValueError(
                "left hand side of the formula  must be a numeric vector or a surival"
            )
    n = _column_len(Y)

    wt = None
    if "(weights)" in mf_names:
        wt = np.asarray(mf_cols[mf_names.index("(weights)")], dtype=float)

    if Terms.get("offset"):
        raise ValueError("Offset terms not allowed")

    stemp = untangle_specials(Terms, "strata")
    strat = None
    if stemp.get("vars"):
        name_to_col = {name: col for name, col in zip(mf_names, mf_cols)}
        if len(stemp["vars"]) == 1:
            strat = name_to_col[stemp["vars"][0]]
        else:
            cols = [name_to_col[v] for v in stemp["vars"]]
            strat = strata_fn(*cols, shortlabel=True)
        for idx in sorted(stemp["terms"], reverse=True):
            Terms = _drop_term(Terms, idx)

    x = _model_matrix_predictor(Terms, mf_names, mf_cols)
    count = _surv_concordance_fit(Y, x, strat, wt)
    if count is None:
        raise ValueError("survConcordance.fit returned NULL")

    if strat is None:
        conc = (count[0] + count[2] / 2) / np.sum(count[:3])
        std_err = count[4] / (2 * np.sum(count[:3]))
    else:
        temp = np.sum(count, axis=0)
        conc = (temp[0] + temp[2] / 2) / np.sum(temp[:3])
        std_err = temp[4] / (2 * np.sum(temp[:3]))

    fit = {
        "concordance": float(conc),
        "stats": count,
        "n": n,
        "std.err": float(std_err),
        "call": call,
        "class_": ("survConcordance",),
    }
    return fit
