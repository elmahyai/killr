"""Expected survival (survival::survexp)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from survival._survexp_core import survexp_fit
from survival.fromtimeline import Categorical
from survival.is_ratetable import is_ratetable
from survival.match_ratetable import match_ratetable
from survival.pyears import (
    Tcut,
    _eval_expr,
    _has_interaction,
    _match_arg,
    _response_matrix,
    _split_terms,
)
from survival.strata import StrataFactor, strata as strata_fn

@dataclass
class _SurvexpFrame:
    response: Any | None
    weights: np.ndarray
    terms: list[str]
    columns: dict[str, Any]
    n: int
    row_names: list[str]


def _coxph_ratetable(obj: Mapping[str, Any]) -> bool:
    klass = obj.get("class_") or obj.get("class") or ()
    if isinstance(klass, str):
        klass = (klass,)
    return "coxph" in klass and "coxphms" not in klass


def _is_coxphms(obj: Mapping[str, Any]) -> bool:
    klass = obj.get("class_") or obj.get("class") or ()
    if isinstance(klass, str):
        klass = (klass,)
    return "coxphms" in klass


def _ratetable_varlist(ratetable: Any) -> list[str]:
    if is_ratetable(ratetable):
        att = ratetable if isinstance(ratetable, dict) else ratetable.__dict__
        names = att.get("dimnames_names") or att.get("dimid")
        if names is None and isinstance(att.get("dimnames"), dict):
            names = list(att["dimnames"].keys())
        return list(names or [])
    if _coxph_ratetable(ratetable):
        raise NotImplementedError("survexp with a coxph ratetable requires survfit.coxph")
    raise ValueError("Invalid rate table")


def _expand_rmap(rmap: dict[str, str] | None, varlist: list[str]) -> dict[str, str]:
    if rmap is None:
        return {name: name for name in varlist}
    out = dict(rmap)
    for name in varlist:
        if name not in out:
            out[name] = name
    return out


def _build_survexp_frame(
    formula: str,
    data: Mapping[str, Any],
    *,
    weights=None,
    subset=None,
    na_action=None,
    extra_vars: list[str] | None = None,
) -> _SurvexpFrame:
    if formula is None or "~" not in formula:
        raise ValueError("A formula argument is required")
    lhs, rhs = formula.split("~", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    if _has_interaction(rhs):
        raise ValueError("Survexp cannot have interaction terms")
    n = len(next(iter(data.values())))
    if subset is not None:
        if callable(subset):
            keep = np.asarray(subset(dict(data)), dtype=bool)
        else:
            keep = np.asarray(subset, dtype=bool)
    else:
        keep = np.ones(n, dtype=bool)
    sub_env: dict[str, Any] = {}
    for key, col in data.items():
        if isinstance(col, Categorical):
            sub_env[key] = Categorical([col.values[i] for i in range(n) if keep[i]], col.levels)
        elif isinstance(col, np.ndarray):
            sub_env[key] = col[keep]
        elif isinstance(col, Tcut):
            sub_env[key] = Tcut(col.values[keep], col.cutpoints, col.labels)
        else:
            sub_env[key] = [col[i] for i in range(n) if keep[i]]
    n = len(next(iter(sub_env.values())))
    row_names = [str(i) for i in range(n)]
    response = None
    if lhs:
        response = _eval_expr(lhs, sub_env)
    term_names = _split_terms(rhs)
    extra = extra_vars or []
    for name in extra:
        if name not in term_names:
            term_names.append(name)
    columns = {}
    for name in term_names:
        columns[name] = _eval_expr(name, sub_env)
    wt = weights
    if wt is not None:
        if isinstance(wt, str):
            wt = sub_env[wt]
        wt = np.asarray(wt, dtype=float).reshape(-1)
        if wt.size != n:
            raise ValueError("weights length mismatch")
    else:
        wt = np.ones(n, dtype=float)
    if na_action is not None:
        raise NotImplementedError("na.action is not supported yet")
    return _SurvexpFrame(
        response=response,
        weights=wt,
        terms=[t for t in _split_terms(rhs)],
        columns=columns,
        n=n,
        row_names=row_names,
    )


def survexp(
    formula: str,
    data: Mapping[str, Any] | None = None,
    weights=None,
    subset=None,
    na_action=None,
    rmap: dict[str, str] | None = None,
    times=None,
    method=None,
    cohort=True,
    conditional=False,
    ratetable=None,
    scale: float = 1.0,
    se_fit=None,
    model: bool = False,
    x: bool = False,
    y: bool = False,
):
    """Compute expected survival for a cohort or per subject (ratetable path)."""
    if ratetable is None:
        raise ValueError("No rate table specified")
    if se_fit is not None and se_fit:
        warnings.warn("se.fit value ignored", stacklevel=2)

    varlist = _ratetable_varlist(ratetable)
    rcall = _expand_rmap(rmap, varlist)
    temp = [name for name in rcall if name not in varlist]
    if temp:
        raise ValueError(f"Variable not found in the ratetable: {temp[0]}")
    mf = _build_survexp_frame(
        formula,
        data or {},
        weights=weights,
        subset=subset,
        na_action=na_action,
        extra_vars=[v for v in rcall.values() if isinstance(v, str)],
    )
    n = mf.n
    if n == 0:
        raise ValueError("Data set has 0 rows")

    if is_ratetable(ratetable) and np.any(mf.weights != 1):
        warnings.warn("weights ignored", stacklevel=2)

    if times is not None:
        times = np.asarray(times, dtype=float).reshape(-1)
        if np.any(times < 0):
            raise ValueError("Invalid time point requested")
        if times.size > 1 and np.any(np.diff(times) < 0):
            raise ValueError("Times must be in increasing order")

    Y = mf.response
    no_y = Y is None
    if no_y:
        if times is None:
            if is_ratetable(ratetable):
                raise ValueError("either a times argument or a response is needed")
        newtime = np.asarray(times, dtype=float)
    else:
        Y, stype, is_surv = _response_matrix(Y)
        if is_surv and stype == "right":
            Y = Y[:, 0]
        elif is_surv:
            raise ValueError("Illegal response value")
        if np.any(Y < 0):
            raise ValueError("Negative follow up time")
        temp_y = np.unique(Y)
        if times is None:
            newtime = np.sort(temp_y)
        else:
            newtime = np.sort(np.unique(np.concatenate([times, temp_y[temp_y < np.max(times)]])))

    method_choices = (
        "ederer",
        "hakulinen",
        "conditional",
        "individual.h",
        "individual.s",
    )
    if method is not None:
        method = _match_arg(method, method_choices)
    else:
        if conditional:
            method = "conditional"
        elif no_y:
            method = "ederer"
        else:
            method = "hakulinen"
        if not cohort:
            method = "individual.s"

    if no_y and method != "ederer":
        raise ValueError("a response is required in the formula unless method='ederer'")

    rdata = {}
    for dim_name, src in rcall.items():
        rdata[dim_name] = mf.columns[src] if isinstance(src, str) else src

    israte = False
    rtemp = None
    if is_ratetable(ratetable):
        israte = True
        if no_y:
            Y = np.full(n, float(np.max(times)))
        rtemp = match_ratetable(rdata, ratetable)
        R = rtemp["R"]
    elif _coxph_ratetable(ratetable):
        if _is_coxphms(ratetable):
            raise ValueError("survexp not defined for multi-state coxph models")
        raise NotImplementedError("survexp with coxph ratetable requires survfit.coxph")
    else:
        raise ValueError("Invalid rate table")

    if method.startswith("individual"):
        if no_y:
            raise ValueError("for individual survival an observation time must be given")
        if not israte:
            raise NotImplementedError("individual survexp with coxph ratetable")
        temp_fit = survexp_fit(
            np.arange(1, n + 1, dtype=int),
            R,
            Y,
            np.array([float(np.max(Y))]),
            True,
            ratetable,
        )
        surv = temp_fit["surv"]
        if method == "individual.s":
            xx = surv
        else:
            xx = -np.log(surv)
        return dict(zip(mf.row_names, xx.reshape(-1)))

    ovars = [v for v in mf.terms if v not in ("1", "0")]
    if len(ovars) == 0:
        X = np.ones(n, dtype=float)
        stratum = StrataFactor([1] * n, ["1"])
    else:
        for var in ovars:
            temp_col = mf.columns[var]
            if isinstance(temp_col, Tcut):
                raise ValueError("Can't use tcut variables in expected survival")
        stratum = strata_fn({name: mf.columns[name] for name in ovars})
        X = np.asarray(stratum.codes, dtype=float)

    if israte:
        temp_fit = survexp_fit(
            X.astype(int),
            R,
            Y,
            newtime,
            method == "conditional",
            ratetable,
        )
    else:
        raise NotImplementedError("survexp.cfit path")

    if times is None:
        n_risk = temp_fit["n"]
        surv = temp_fit["surv"]
    else:
        keep = np.array([np.where(newtime == t)[0][0] for t in times], dtype=int)
        if np.ndim(temp_fit["surv"]) > 1:
            base = np.vstack([np.ones((1, temp_fit["surv"].shape[1])), temp_fit["surv"]])
            surv = base[keep + 1, :]
            n_risk = temp_fit["n"][np.maximum(0, keep), :]
        else:
            base = np.concatenate([[1.0], np.asarray(temp_fit["surv"]).reshape(-1)])
            surv = base[keep + 1]
            n_risk = temp_fit["n"][np.maximum(0, keep)]
        newtime = times

    newtime = newtime / scale
    if np.ndim(surv) > 1:
        out = {
            "surv": surv.reshape(-1),
            "n.risk": n_risk.reshape(-1),
            "time": newtime,
        }
    else:
        out = {
            "surv": np.asarray(surv, dtype=float).reshape(-1),
            "n.risk": np.asarray(n_risk, dtype=float).reshape(-1),
            "time": newtime,
        }
    if model:
        out["model"] = mf
    else:
        if x:
            out["x"] = X
        if y:
            out["y"] = Y
    if israte and rtemp and rtemp.get("summ") is not None:
        out["summ"] = rtemp["summ"]
    if no_y:
        out["method"] = "Ederer"
    elif conditional:
        out["method"] = "conditional"
    else:
        out["method"] = "cohort"
    out["class_"] = ("survexp", "survfit")
    return out
