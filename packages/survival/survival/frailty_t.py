"""Student-t frailty penalty term (survival::frailty.t)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from survival.frailty_gamma import (
    _MISSING,
    _factorize,
    _is_missing,
    _pchisq,
    _r_format,
)
from survival.pspline import _frailty_controldf, _frailty_controlaic
from survival.wtest import coxph_wtest


@dataclass
class TFrailtyPenalty:
    """Group frailty predictor with Cox penalty metadata (R ``coxph.penalty``)."""

    data: np.ndarray
    sparse: bool
    levels: list[str]
    pfun: Callable[..., dict[str, Any]]
    printfun: Callable[..., dict[str, Any]]
    cfun: Callable[..., dict[str, Any]]
    cparm: dict[str, Any]
    pparm: float
    cargs: tuple[str, ...] | list[str] = field(default_factory=list)
    diag: bool = True
    varname: list[str] = field(default_factory=list)


def _make_pfun(tdf: float) -> Callable[..., dict[str, Any]]:
    def pfun(coef, theta, ndead):
        del ndead
        coef_arr = np.asarray(coef, dtype=float).reshape(-1)
        if theta == 0:
            return {"recenter": 0.0, "penalty": 0.0, "flag": True}
        sig = float(theta) * (tdf - 2.0) / tdf
        temp = 1.0 + coef_arr**2 / (tdf * sig)
        temp1 = coef_arr / temp
        temp2 = 1.0 / temp - (2.0 / (tdf * sig)) * coef_arr**2 / temp**2
        recenter = float(np.sum(temp1) / np.sum(temp2))
        centered = coef_arr - recenter
        const = (tdf + 1.0) / (tdf * sig)
        temp = 1.0 + centered**2 / (tdf * sig)
        lconst = math.lgamma(tdf / 2.0) - math.lgamma((tdf + 1.0) / 2.0)
        penalty = float(
            np.sum(
                0.5 * np.log(np.pi * tdf * sig)
                + ((tdf + 1.0) / 2.0) * np.log(temp)
                + lconst
            )
        )
        return {
            "recenter": recenter,
            "first": const * centered / temp,
            "second": const * (1.0 / temp - (2.0 / (tdf * sig)) * centered**2 / temp**2),
            "penalty": penalty,
            "flag": False,
        }

    return pfun


def _make_printfun() -> Callable[..., dict[str, Any]]:
    def printfun(coef, var, var2, df, history):
        hist = history.get("history")
        if hist is not None:
            hist_arr = np.asarray(hist, dtype=float)
            if hist_arr.ndim == 2:
                theta = float(hist_arr[-1, 0])
            else:
                theta = float(hist_arr.reshape(-1)[0])
        else:
            theta = float(history["theta"])
        var_arr = np.asarray(var, dtype=float)
        coef_arr = np.asarray(coef, dtype=float).reshape(-1)
        if var_arr.ndim == 2:
            test = float(coxph_wtest(var_arr, coef_arr)["test"])
        else:
            test = float(np.sum(coef_arr**2 / var_arr.reshape(-1)))
        df2 = max(float(df), 0.5)
        pval = _pchisq(test, df2, lower_tail=False)
        coef_out = np.array([math.nan, math.nan, math.nan, test, df, pval], dtype=float)
        hist_str = " ".join(("Variance of random effect=", _r_format(theta)))
        return {"coef": coef_out, "history": hist_str}

    return printfun


def _fixed_cfun(parms, iter_, old):
    del iter_, old
    return {"theta": float(parms["theta"]), "done": True}


def frailty_t(
    x: Any,
    sparse: Any = _MISSING,
    theta: Any = _MISSING,
    df: Any = _MISSING,
    eps: float = 1e-5,
    tdf: float = 5.0,
    method: Any = _MISSING,
    **kwargs: Any,
) -> TFrailtyPenalty:
    """Build a t-distribution frailty penalty term for Cox models."""
    if tdf <= 2:
        raise ValueError("Cannot have df <3 for the t-frailty")

    raw = np.asarray(x, dtype=object).reshape(-1)
    valid = raw.copy()
    na_mask = np.array(
        [v is None or (isinstance(v, float) and np.isnan(v)) for v in valid],
        dtype=bool,
    )
    if np.issubdtype(np.asarray(x).dtype, np.number):
        na_mask = np.isnan(np.asarray(x, dtype=float).reshape(-1))
        valid = np.asarray(x, dtype=float).reshape(-1)
    unique_vals = valid[~na_mask]
    nclass = len(np.unique(unique_vals)) if unique_vals.size else 0

    if _is_missing(sparse):
        sparse_flag = nclass > 5
    else:
        sparse_flag = bool(sparse)

    codes, labels, levels = _factorize(np.asarray(x, dtype=object).reshape(-1))
    data = codes.copy() if sparse_flag else labels.copy()
    vec_len = len(raw)

    method_val = method
    if _is_missing(method_val):
        if not _is_missing(theta):
            method_val = "fixed"
            if not _is_missing(df):
                raise ValueError("Cannot give both a df and theta argument")
        elif not _is_missing(df):
            method_val = "aic" if float(df) == 0 else "df"
        else:
            method_val = "aic"

    method_str = str(method_val)
    allowed = ("aic", "df", "fixed")
    if method_str not in allowed:
        raise ValueError(f"'{method_str}' is not a valid method")

    if method_str == "df" and _is_missing(df):
        raise ValueError("Method = df but no df argument")
    if method_str == "fixed" and _is_missing(theta):
        raise ValueError("Method= fixed but no theta argument")
    if method_str != "fixed" and not _is_missing(theta):
        raise ValueError("Method is not 'fixed', but have a theta argument")

    pfun = _make_pfun(float(tdf))
    printfun = _make_printfun()

    if method_str == "fixed":
        cparm = {"theta": float(theta), **kwargs}
        cfun: Callable[..., dict[str, Any]] = _fixed_cfun
        cargs: list[str] = []
    elif method_str == "aic":
        cparm = {"eps": eps, "lower": 0.0, "init": np.array([0.1, 1.0]), **kwargs}
        cfun = _frailty_controlaic
        cargs = ["neff", "df", "plik"]
    else:
        df_eps = 0.1 if eps == 1e-5 else eps
        cparm = {
            "df": float(df),
            "thetas": 0.0,
            "dfs": 0.0,
            "eps": df_eps,
            "guess": 3.0 * float(df) / vec_len,
            **kwargs,
        }
        cfun = _frailty_controldf
        cargs = ["df"]

    varname: list[str] = []
    if not sparse_flag:
        varname = [f"t:{level}" for level in levels]

    return TFrailtyPenalty(
        data=data,
        sparse=sparse_flag,
        levels=levels,
        pfun=pfun,
        printfun=printfun,
        cfun=cfun,
        cparm=cparm,
        pparm=float(tdf),
        cargs=cargs,
        diag=True,
        varname=varname,
    )
