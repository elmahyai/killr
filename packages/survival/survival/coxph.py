"""Cox proportional hazards model (survival::coxph).

Scope of this translation, checked against R in proof/coxph.R:

- right-censored responses Surv(time, status), via coxph_fit for the Breslow
  and Efron ties and via the coxexact crate for ties = "exact";
- strata(), offset(), numeric and factor main effects and interactions in the
  model matrix, case weights, subset, and na.action (default na.omit). Only the
  unweighted fit with default na.action is covered by proof/coxph.R; weights,
  subset, and explicit na.action are implemented but not proven;
- singular columns (coefficients set to NA), the zero-event result, and the
  Wald test on the coefficients.

Not translated (NotImplementedError is raised, as R would take another path):
counting-process responses (agreg.fit and agexact.fit kernels), robust
variance, cluster() and id terms, tt(), frailty(), ridge(), pspline(), and
multi-state models. The exact-method martingale residuals need the
Ccoxmart2 kernel, which is not in a crate, so residuals are None there.
"""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

import numpy as np

from survival._coxexact import coxexact_fit
from survival.coxph_fit import coxph_fit
from survival.control import coxph_control
from survival.fromtimeline import Categorical
from survival.strata import StrataFactor, strata as strata_fn
from survival.surv import SurvObject, Surv, aeqSurv, is_Surv
from survival.surv_split import _apply_subset, _as_table
from survival.survobrien import (
    _apply_na_action,
    _build_terms,
    _eval_expr,
    _parse_call_args,
    _split_terms,
)
from survival._yates_mm import build_terms, model_matrix, _term_labels_from_rhs
from survival.wtest import coxph_wtest


_UNSUPPORTED_SPECIALS = ("cluster(", "tt(", "frailty(", "ridge(", "pspline(")
_METHODS = ("efron", "breslow", "exact")


class _Missing:
    pass


_missing = _Missing()


def _match_arg(value: Any, choices: tuple[str, ...]) -> str:
    if value is None:
        return choices[0]
    text = str(value)
    hits = [c for c in choices if c == text or c.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ValueError(f"'{text}' is ambiguous")
    raise ValueError(f"'{text}' should be one of {', '.join(choices)}")


def _data_class(name: str, col: Any) -> str:
    del name
    if isinstance(col, (Categorical, StrataFactor)):
        return "factor"
    if isinstance(col, (list, tuple)):
        if col and not isinstance(col[0], (list, tuple, dict)):
            sample = col[0]
            if sample is None or isinstance(sample, (int, float)):
                return "numeric"
            return "factor"
    if isinstance(col, np.ndarray):
        if col.dtype.kind in "iuf":
            return "numeric"
        return "factor"
    return "numeric"


def _as_vector(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return np.asarray(value)
    return value


def _is_offset_term(term: str) -> bool:
    return term.strip().lower().startswith("offset(")


def _frame_columns(
    formula: str,
    table: Mapping[str, Any],
    *,
    weights: Any,
    subset: Any,
    na_action: Any,
) -> tuple[list[str], list[Any], dict[str, Any], list[str], list[str]]:
    """Build the model frame. Returns names, columns, terms, pred labels, and special names."""
    if formula is None or "~" not in str(formula):
        raise ValueError("A formula argument is required")
    lhs, rhs = str(formula).split("~", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    for special in _UNSUPPORTED_SPECIALS:
        if special in rhs.lower():
            raise NotImplementedError(f"{special[:-1]}() terms are not translated for coxph")

    table, keep = _apply_subset(dict(table), subset)
    env = dict(table)
    response = _eval_expr(lhs, env)
    if not is_Surv(response):
        raise ValueError("response must be a survival object")
    if response.type not in ("right",):
        raise NotImplementedError(
            f"Cox model for '{response.type}' survival data (counting process) is not translated"
        )

    term_exprs = _split_terms(rhs)
    term_labels: list[str] = []
    mf_names = [lhs]
    mf_cols: list[Any] = [response]
    specials: dict[str, list[int]] = {}
    pred_labels: list[str] = []

    if weights is not None:
        if isinstance(weights, str):
            weight_col = np.asarray(table[weights], dtype=float)
        else:
            weight_col = np.asarray(weights, dtype=float).reshape(-1)
            if keep is not None:
                weight_col = weight_col[keep]
        mf_names.append("(weights)")
        mf_cols.append(weight_col)
        specials.setdefault("weights", []).append(len(mf_names))

    for term in term_exprs:
        term_labels.append(term)
        lower = term.lower()
        if lower.startswith("strata("):
            args = _parse_call_args(term, "strata")
            if not args:
                raise ValueError("strata() needs at least one variable")
            values = [_as_vector(_eval_expr(a, env)) for a in args]
            if len(values) == 1:
                col = strata_fn(values[0])
            else:
                col = strata_fn(*values, shortlabel=True)
            mf_names.append(term)
            mf_cols.append(col)
            specials.setdefault("strata", []).append(len(mf_names))
            continue
        if _is_offset_term(term):
            col = _eval_expr(_parse_call_args(term, "offset")[0], env)
            mf_names.append(term)
            mf_cols.append(col)
            specials.setdefault("offset", []).append(len(mf_names))
            continue
        if ":" in term:
            if "strata(" in term.lower():
                raise NotImplementedError("strata() inside an interaction is not translated")
            pred_labels.append(term)
            continue
        col = _eval_expr(term, env)
        mf_names.append(term)
        mf_cols.append(col)
        pred_labels.append(term)

    mf_names, mf_cols = _apply_na_action(mf_names, mf_cols, na_action)
    terms = _build_terms(mf_names, term_labels, specials)
    return mf_names, mf_cols, terms, pred_labels, term_labels


def _model_matrix_for(
    pred_labels: list[str],
    mf_names: list[str],
    mf_cols: list[Any],
    table: Mapping[str, Any],
    n: int,
) -> tuple[np.ndarray, list[str]]:
    if not pred_labels:
        return np.zeros((n, 0), dtype=float), []
    env = dict(table)
    for name, col in zip(mf_names, mf_cols):
        if name.startswith("("):
            continue
        env[name] = col
    rhs = " + ".join(pred_labels)
    pred_data: dict[str, Any] = {"y": np.zeros(n, dtype=float)}
    _intercept, rhs_labels = _term_labels_from_rhs(rhs)
    seen: set[str] = set()
    for label in rhs_labels:
        parts = label.split(":") if ":" in label else [label]
        for part in parts:
            if part in seen:
                continue
            seen.add(part)
            val = _eval_expr(part, env)
            if isinstance(val, Categorical):
                val = val.values
            pred_data[part] = val
    yterms = build_terms(f"y ~ 0 + {rhs}", pred_data)
    for name in yterms.variables[1:]:
        yterms.data_classes[name] = _data_class(name, pred_data[name])
    xlevels: dict[str, list[str]] = {}
    for name in yterms.variables[1:]:
        if yterms.data_classes.get(name) == "factor":
            col = pred_data[name]
            if isinstance(col, Categorical):
                xlevels[name] = list(col.levels)
            elif name in env and isinstance(env[name], Categorical):
                xlevels[name] = list(env[name].levels)
            else:
                levels: list[str] = []
                for v in col:
                    text = str(v)
                    if text not in levels:
                        levels.append(text)
                xlevels[name] = levels
    x, xnames, _assign = model_matrix(yterms, pred_data, xlevels=xlevels)
    return np.asarray(x, dtype=float), xnames


def _fit_exact(
    x: np.ndarray,
    y: np.ndarray,
    strata: np.ndarray | None,
    offset: np.ndarray,
    control: dict[str, Any],
    nocenter: Any,
) -> dict[str, Any]:
    """Conditional likelihood fit (survival coxexact.fit), without the residuals."""
    n, nvar = x.shape
    if strata is None or np.size(strata) == 0:
        sorted_idx = np.argsort(-y[:, 0], kind="stable")
        newstrat = np.zeros(n, dtype=np.int32)
    else:
        strata_arr = np.asarray(strata, dtype=float).reshape(-1)
        sorted_idx = np.lexsort((-y[:, 0], strata_arr))
        strata_sorted = strata_arr[sorted_idx]
        newstrat = np.ones(n, dtype=np.int32)
        if n > 1:
            newstrat[1:] = (np.diff(strata_sorted) != 0).astype(np.int32)
    ysorted = np.ascontiguousarray(y[sorted_idx, :], dtype=float)
    off = offset[sorted_idx]
    if nvar == 0:
        raise NotImplementedError("null model for the exact method is not translated")
    xs = x[sorted_idx, :]
    means = xs.mean(axis=0)
    rescale = xs.std(axis=0, ddof=1)
    newx = (xs - means) / rescale
    if nocenter is not None:
        allowed = np.asarray(list(nocenter), dtype=float)
        for i in range(nvar):
            if np.all(np.isin(x[:, i], allowed)):
                newx[:, i] = xs[:, i]
                rescale[i] = 1.0
                means[i] = 0.0
    ex = coxexact_fit(
        maxiter=int(control["iter.max"]),
        y=ysorted,
        x=newx,
        offset=off,
        strata=newstrat,
        init=None,
        eps=float(control["eps"]),
        toler_chol=float(control["toler.chol"]),
        rescale=rescale,
        means=means,
    )
    coef_scaled = np.asarray(ex["coef"], dtype=float) * rescale
    lp_sorted = newx @ coef_scaled + off
    lp = np.zeros(n, dtype=float)
    lp[sorted_idx] = lp_sorted
    return {
        "coef": np.asarray(ex["coef"], dtype=float),
        "var": np.asarray(ex["var"], dtype=float),
        "loglik": np.asarray(ex["loglik"], dtype=float),
        "score": float(ex["sctest"]),
        "iter": int(ex["iter"]),
        "means": np.asarray(ex["means"], dtype=float),
        "linear.predictors": lp,
        "which_sing": np.asarray(ex["which_sing"], dtype=bool),
    }


def _zero_event_fit(x: np.ndarray, offset: np.ndarray, n: int, nevent: float, method: str) -> dict[str, Any]:
    ncoef = x.shape[1]
    return {
        "coefficients": np.full(ncoef, np.nan),
        "var": np.zeros((ncoef, ncoef), dtype=float),
        "loglik": np.array([0.0, 0.0]),
        "score": 0.0,
        "iter": 0,
        "linear.predictors": offset,
        "residuals": np.zeros(n, dtype=float),
        "means": x.mean(axis=0) if ncoef else np.zeros(0),
        "method": method,
        "n": n,
        "nevent": nevent,
        "class_": ("coxph",),
    }


def coxph(
    formula: str,
    data: Mapping[str, Any] | None = None,
    weights: Any = None,
    subset: Any = None,
    na_action: Any = None,
    init: Any = None,
    control: dict[str, Any] | None = None,
    ties: str = "efron",
    singular_ok: bool = True,
    robust: Any = None,
    model: bool = False,
    x: bool = False,
    y: bool = True,
    tt: Any = None,
    method: str | None = None,
    id: Any = None,
    cluster: Any = None,
    nocenter: Any = (-1, 0, 1),
    **kwargs: Any,
) -> dict[str, Any]:
    """Fit a Cox proportional hazards model (right-censored responses)."""
    del model, tt
    if formula is None:
        raise ValueError("a formula argument is required")
    ties_name = _match_arg(ties, _METHODS)
    method_name = _match_arg(method, _METHODS) if method is not None else ties_name
    if control is None:
        ctrl = coxph_control(**kwargs)
    else:
        if kwargs:
            raise TypeError(f"unexpected arguments with control: {', '.join(kwargs)}")
        ctrl = control
    if id is not None or cluster is not None:
        raise NotImplementedError("id and cluster terms are not translated for coxph")
    if robust is True:
        raise NotImplementedError("robust variance is not translated for coxph")
    if init is not None and np.size(init) > 0 and np.any(np.asarray(init, dtype=float) != 0):
        raise NotImplementedError("non-zero init is not translated for coxph")

    table = _as_table(data) if data is not None else {}
    if isinstance(weights, _Missing):
        weights = None

    mf_names, mf_cols, terms, pred_labels, _labels = _frame_columns(
        str(formula),
        table,
        weights=weights,
        subset=subset,
        na_action=na_action,
    )
    if len(mf_cols) == 0 or len(mf_cols[0]) == 0:
        raise ValueError("No (non-missing) observations")

    if ctrl["timefix"]:
        response = aeqSurv(mf_cols[0])
    else:
        response = mf_cols[0]
    Y = np.asarray(response.columns, dtype=float)
    n = Y.shape[0]
    nevent = float(np.sum(Y[:, -1]))

    strata_names = terms["specials"].get("strata") or []
    strata_codes = None
    if strata_names:
        if len(strata_names) > 1:
            raise NotImplementedError("more than one strata() term is not translated")
        strata_col = mf_cols[strata_names[0] - 1]
        if isinstance(strata_col, StrataFactor):
            strata_codes = np.array([0 if c is None else int(c) for c in strata_col.codes], dtype=int)
        else:
            strata_codes = np.asarray(strata_col, dtype=int)

    offset_idx = terms["specials"].get("offset") or []
    if offset_idx:
        offset = np.zeros(n, dtype=float)
        for idx in offset_idx:
            offset = offset + np.asarray(mf_cols[idx - 1], dtype=float).reshape(-1)
    else:
        offset = np.zeros(n, dtype=float)
    if np.any(~np.isfinite(offset)) or np.any(~np.isfinite(np.exp(offset))):
        raise ValueError("offsets must lead to a finite risk score")
    meanoffset = 0.0
    if np.any(offset != 0):
        meanoffset = float(np.mean(offset))
        offset = offset - meanoffset

    weight_idx = terms["specials"].get("weights") or []
    wt = np.asarray(mf_cols[weight_idx[0] - 1], dtype=float) if weight_idx else None
    if wt is not None and np.any(~np.isfinite(wt)):
        raise ValueError("weights must be finite")
    if wt is not None and np.any(wt <= 0):
        raise ValueError("Invalid weights, must be >0")
    if wt is not None and np.any(wt != np.floor(wt)) and robust is None:
        raise NotImplementedError("non-integer weights need the robust variance, not translated")

    X, xnames = _model_matrix_for(pred_labels, mf_names, mf_cols, table, n)
    if X.shape[1] and not np.all(np.isfinite(X)):
        raise ValueError("data contains an infinite predictor")

    if np.sum(Y[:, -1]) == 0:
        out = _zero_event_fit(X, offset, n, nevent, method_name)
        out["terms"] = terms
        out["formula"] = str(formula)
        return out

    if method_name == "exact":
        if wt is not None:
            raise ValueError("Case weights are not supported for the exact method")
        if strata_codes is None:
            strata_codes = np.zeros(n, dtype=int)
        fit = _fit_exact(X, Y, strata_codes, offset, ctrl, nocenter)
        coef = fit["coef"].astype(float)
        var = fit["var"].reshape(X.shape[1], X.shape[1])
        coef = coef.copy()
        coef[fit["which_sing"]] = np.nan
        fit_resid = None
        lp = fit["linear.predictors"]
        means = fit["means"]
    else:
        fit = coxph_fit(
            X,
            Y,
            strata_codes,
            offset,
            init,
            ctrl,
            wt,
            method_name,
            None,
            True,
            nocenter,
        )
        fit_resid = fit.get("residuals")
        if X.shape[1] == 0:
            # coxph.null: only the loglik (one value), the offset as predictor
            return {
                "loglik": np.atleast_1d(np.asarray(fit["loglik"], dtype=float)),
                "linear.predictors": offset + meanoffset,
                "residuals": np.asarray(fit_resid, dtype=float),
                "method": method_name,
                "n": n,
                "nevent": nevent,
                "terms": terms,
                "class_": ("coxph.null", "coxph"),
                "formula": str(formula),
            }
        coef = np.asarray(fit["coefficients"], dtype=float)
        var = np.asarray(fit["var"], dtype=float)
        lp = np.asarray(fit["linear.predictors"], dtype=float)
        means = np.asarray(fit["means"], dtype=float)

    out: dict[str, Any] = {
        "coefficients": dict(zip(xnames, coef)) if X.shape[1] else {},
        "var": var,
        "loglik": np.asarray(fit["loglik"], dtype=float),
        "score": float(fit["score"]),
        "iter": int(fit["iter"]),
        "linear.predictors": lp + meanoffset if meanoffset != 0 else lp,
        "means": means,
        "method": method_name,
        "n": n,
        "nevent": nevent,
        "terms": terms,
        "class_": ("coxph",),
    }
    if fit_resid is not None:
        out["residuals"] = np.asarray(fit_resid, dtype=float)
    else:
        out["residuals"] = None

    if X.shape[1] and not np.all(np.isnan(coef)):
        nabeta = ~np.isnan(coef)
        temp = coef[nabeta]
        out["wald.test"] = coxph_wtest(var[np.ix_(nabeta, nabeta)], temp, ctrl["toler.chol"])["test"]
    if x:
        out["x"] = X
    if y:
        out["y"] = Y
    out["formula"] = str(formula)
    out["singular.ok"] = singular_ok
    return out
