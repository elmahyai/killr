"""Gaussian frailty penalty term (survival::frailty.gaussian)."""

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
class GaussianFrailtyPenalty:
    """Group frailty predictor with Cox penalty metadata (R ``coxph.penalty``)."""

    data: np.ndarray
    sparse: bool
    levels: list[str]
    pfun: Callable[..., dict[str, Any]]
    printfun: Callable[..., dict[str, Any]]
    cfun: Callable[..., dict[str, Any]]
    cparm: dict[str, Any]
    cargs: tuple[str, ...] | list[str] = field(default_factory=list)
    diag: bool = True
    varname: list[str] = field(default_factory=list)


def _frailty_controlgauss(
    opt: dict[str, Any],
    iter_: int,
    old: dict[str, Any],
    fcoef: Any = None,
    trH: float | None = None,
    loglik: float | None = None,
) -> dict[str, Any]:
    del loglik
    if iter_ == 0:
        if opt.get("theta") is not None:
            theta = float(opt["theta"])
        else:
            init = opt.get("init")
            theta = 1.0 if init is None else float(np.asarray(init).reshape(-1)[0])
        return {"theta": theta}

    trace = bool(opt.get("trace", False))
    fcoef_arr = np.asarray(fcoef, dtype=float).reshape(-1)
    nfrail = fcoef_arr.size
    fsum = float(np.sum(fcoef_arr**2))
    theta = float(old["theta"])
    tr_h = float(trH)
    resid = fsum / (nfrail - tr_h / theta) - theta

    if iter_ == 1:
        history = np.array([[theta, resid, fsum, tr_h]], dtype=float)
        init = opt.get("init")
        if init is None:
            next_theta = theta * 3.0 if resid > 0 else theta / 3.0
        else:
            next_theta = float(np.asarray(init).reshape(-1)[1])
        return {"theta": float(next_theta), "done": False, "history": history}

    history_old = np.asarray(old["history"], dtype=float)
    if history_old.ndim == 1:
        history_old = history_old.reshape(1, -1)
    row = np.array([[theta, resid, fsum, tr_h]], dtype=float)
    history = np.vstack((history_old, row))

    if iter_ == 2:
        if np.all(history[:, 1] > 0):
            next_theta = history[1, 0] * 2.0
        elif np.all(history[:, 1] < 0):
            next_theta = history[1, 0] / 2.0
        else:
            next_theta = float(np.mean(history[:2, 0]))
        if trace:
            print(history)
            print(f"    new theta= {next_theta} \n\n")
        return {"theta": float(next_theta), "done": False, "history": history}

    done = abs(history[iter_ - 1, 1]) < float(opt["eps"])
    ord_idx = np.argsort(history[:, 0])
    tempy = history[ord_idx, 1]
    tempx = history[ord_idx, 0]

    if np.all(tempy > 0):
        newtheta = 2.0 * float(np.max(tempx))
    elif np.all(tempy < 0):
        newtheta = 0.5 * float(np.min(tempx))
    else:
        b1 = int(np.where(ord_idx == iter_ - 1)[0][0])
        if b1 == 0:
            b1 = 1
        elif b1 == iter_ - 1:
            b1 = iter_ - 2
        r_val = tempy[b1] / tempy[b1 + 1]
        s_val = tempy[b1] / tempy[b1 - 1]
        u_val = r_val / s_val
        p_val = s_val * (
            u_val * (r_val - u_val) * (tempx[b1 + 1] - tempx[b1])
            - (1.0 - r_val) * (tempx[b1] - tempx[b1 - 1])
        )
        q_val = (u_val - 1.0) * (r_val - 1.0) * (s_val - 1.0)
        newtheta = tempx[b1] + p_val / q_val
        if newtheta > tempx[b1 + 1]:
            newtheta = float(np.mean(tempx[b1 : b1 + 2]))
        if newtheta < tempx[b1 - 1]:
            newtheta = float(np.mean(tempx[b1 - 1 : b1 + 1]))

    if trace:
        print(history)
        print(f"    new theta= {_r_format(newtheta)} \n\n")
    return {"theta": float(newtheta), "done": bool(done), "history": history}


def _make_printfun() -> Callable[..., dict[str, Any]]:
    def printfun(coef, var, var2, df, history):
        del var2
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


def _make_pfun() -> Callable[..., dict[str, Any]]:
    def pfun(coef, theta, ndeath):
        del ndeath
        coef_arr = np.asarray(coef, dtype=float).reshape(-1)
        if theta == 0:
            return {"recenter": 0.0, "penalty": 0.0, "flag": True}
        recenter = float(np.mean(coef_arr))
        centered = coef_arr - recenter
        th = float(theta)
        penalty = 0.5 * float(np.sum(centered**2 / th + math.log(2.0 * math.pi * th)))
        return {
            "recenter": recenter,
            "first": centered / th,
            "second": np.ones(centered.size, dtype=float) / th,
            "penalty": penalty,
            "flag": False,
        }

    return pfun


def _fixed_cfun(opt: dict[str, Any], iter_: int, old: dict[str, Any]) -> dict[str, Any]:
    del iter_, old
    return {"theta": float(opt["theta"]), "done": True}


def frailty_gaussian(
    x: Any,
    sparse: Any = _MISSING,
    theta: Any = _MISSING,
    df: Any = _MISSING,
    method: Any = _MISSING,
    **kwargs: Any,
) -> GaussianFrailtyPenalty:
    """Build a Gaussian frailty penalty term for Cox or survreg models."""
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

    method_val = method
    if _is_missing(method_val):
        if not _is_missing(theta):
            method_val = "fixed"
            if not _is_missing(df):
                raise ValueError("Cannot give both a df and theta argument")
        elif not _is_missing(df):
            if float(df) == 0:
                method_val = "aic"
            else:
                method_val = "df"
        else:
            method_val = "reml"

    method_str = str(method_val)
    allowed = ("reml", "aic", "df", "fixed")
    if method_str not in allowed:
        raise ValueError(f"'{method_str}' is not a valid method")

    if method_str == "df" and _is_missing(df):
        raise ValueError("Method = df but no df argument")
    if method_str == "fixed" and _is_missing(theta):
        raise ValueError("Method= fixed but no theta argument")
    if method_str != "fixed" and not _is_missing(theta):
        raise ValueError("Method is not 'fixed', but have a theta argument")
    if not _is_missing(theta) and not _is_missing(df):
        raise ValueError("Cannot give both a df and theta argument")

    pfun = _make_pfun()
    printfun = _make_printfun()

    if method_str == "reml":
        cparm = dict(kwargs)
        cfun: Callable[..., dict[str, Any]] = _frailty_controlgauss
        cargs = ("fcoef", "trH", "loglik")
    elif method_str == "fixed":
        cparm = {"theta": float(theta), **kwargs}
        cfun = _fixed_cfun
        cargs = ()
    elif method_str == "aic":
        cparm = {"lower": 0.0, "init": np.array([0.1, 1.0]), **kwargs}
        cfun = _frailty_controlaic
        cargs = ("neff", "df", "plik")
    else:
        cparm = {
            "df": float(df),
            "thetas": 0.0,
            "dfs": 0.0,
            "guess": 3.0 * float(df) / len(codes),
            **kwargs,
        }
        cfun = _frailty_controldf
        cargs = ("df",)

    varname: list[str] = []
    if not sparse_flag:
        varname = [f"gauss:{level}" for level in levels]

    return GaussianFrailtyPenalty(
        data=data,
        sparse=sparse_flag,
        levels=levels,
        pfun=pfun,
        printfun=printfun,
        cfun=cfun,
        cparm=cparm,
        cargs=list(cargs),
        diag=True,
        varname=varname,
    )
