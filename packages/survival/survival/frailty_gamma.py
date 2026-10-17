"""Gamma frailty penalty term (survival::frailty.gamma)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from survival.pspline import _frailty_brent, _frailty_controldf, _frailty_controlaic
from survival.wtest import coxph_wtest

_MISSING = object()


@dataclass
class GammaFrailtyPenalty:
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


def _is_missing(value: Any) -> bool:
    return value is _MISSING


def _pchisq(q: float, df: float, *, lower_tail: bool = False) -> float:
    if df <= 0:
        return math.nan
    if df == 1:
        root = math.sqrt(max(float(q), 0.0))
        pnorm = 0.5 * (1.0 + math.erf(root / math.sqrt(2.0)))
        upper = 2.0 * (1.0 - pnorm)
        return 1.0 - upper if lower_tail else upper
    from survival.gamma import _pgamma_raw

    shape = df / 2.0
    x = q / 2.0
    cdf = _pgamma_raw(x, shape)
    return cdf if lower_tail else 1.0 - cdf


def _frailty_gammacon(d: np.ndarray, nu: float) -> float:
    d = np.asarray(d, dtype=float).reshape(-1)
    maxd = int(np.max(d)) if d.size else 0
    if maxd == 0:
        return 0.0
    if nu > 1e7 * maxd:
        term1 = float(np.sum(d * d) / nu)
    else:
        term1 = float(np.sum(d + nu * np.log(nu / (nu + d))))

    positive = d[d > 0]
    if positive.size == 0:
        return term1
    levels = np.arange(1, maxd + 1, dtype=float)
    tbl = np.array([(positive == lev).sum() for lev in levels], dtype=float)
    ctbl = np.cumsum(tbl[::-1])[::-1]
    dlev = levels
    numerators = []
    denominators = []
    for i, lev in enumerate(dlev):
        count = int(tbl[i])
        if count == 0:
            continue
        numerators.extend([nu + (lev - 1.0)] * int(ctbl[i]))
        denominators.extend([nu + lev] * int(count * lev))
    term2 = float(np.sum(np.log(np.asarray(numerators) / np.asarray(denominators))))
    return term1 + term2


def _group_death_counts(group: Any, status: Any) -> np.ndarray:
    status = np.asarray(status, dtype=float).reshape(-1)
    if isinstance(group, np.ndarray) and group.ndim == 2:
        ncol = group.shape[1]
        cols = np.arange(1, ncol + 1, dtype=float)
        group = group @ cols
    group = np.asarray(group).reshape(-1)
    unique = np.unique(group[~np.isnan(group.astype(float, copy=False)) if group.dtype.kind == "f" else group])
    if group.dtype.kind in "iu" or group.dtype.kind == "f":
        order = np.sort(unique)
    else:
        order = np.unique(group, return_inverse=False)
    counts = []
    for level in order:
        mask = group == level
        counts.append(float(np.sum(status[mask])))
    return np.asarray(counts, dtype=float)


def _loglik_correction(theta: float, group: Any, status: Any) -> float:
    if theta == 0:
        return 0.0
    d = _group_death_counts(group, status)
    return _frailty_gammacon(d, 1.0 / theta)


def _frailty_controlgam(
    opt: dict[str, Any],
    iter_: int,
    old: dict[str, Any],
    group: Any,
    status: Any,
    loglik: float,
) -> dict[str, Any]:
    if iter_ == 0:
        if opt.get("theta") is not None:
            theta = float(opt["theta"])
        else:
            init = opt.get("init")
            theta = 0.0 if init is None else float(np.asarray(init).reshape(-1)[0])
        return {"theta": theta}

    trace = bool(opt.get("trace", False))
    theta = float(old["theta"])
    correct = _loglik_correction(theta, group, status)
    full = loglik + correct

    if opt.get("theta") is not None:
        return {"theta": theta, "done": True, "c.loglik": full}

    if iter_ == 1:
        history = np.array([[theta, loglik, full]], dtype=float)
        init = opt.get("init")
        next_theta = 1.0 if init is None else float(np.asarray(init).reshape(-1)[1])
        return {"theta": next_theta, "done": False, "history": history, "c.loglik": full}

    history = np.asarray(old["history"], dtype=float)
    if history.ndim == 1:
        history = history.reshape(1, -1)
    row = np.array([[theta, loglik, full]], dtype=float)
    history = np.vstack((history, row))

    if iter_ == 2:
        if history[1, 2] < history[0, 2] + 1:
            next_theta = float(np.mean(history[:2, 0]))
        else:
            next_theta = 2.0 * history[1, 0]
        if trace:
            print(history)
            print(f"    new theta= {next_theta} \n\n")
        return {"theta": next_theta, "done": False, "history": history, "c.loglik": full}

    done = abs(1.0 - history[iter_ - 1, 2] / history[iter_ - 2, 2]) < float(opt["eps"])
    x = history[:, 0]
    y = history[:, 2]
    if y[iter_ - 1] == np.max(y) and x[iter_ - 1] == np.max(x):
        newtheta = 2.0 * float(np.max(x))
    else:
        newtheta = _frailty_brent(np.sqrt(x), y, lower=0.0) ** 2
    if trace:
        print(history)
        print(f"    new theta= {newtheta} \n\n")
    return {"theta": float(newtheta), "done": bool(done), "history": history, "c.loglik": full}


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
        clog = float(history["c.loglik"])
        var_arr = np.asarray(var, dtype=float)
        coef_arr = np.asarray(coef, dtype=float).reshape(-1)
        if var_arr.ndim == 2:
            test = float(coxph_wtest(var_arr, coef_arr)["test"])
        else:
            test = float(np.sum(coef_arr**2 / var_arr.reshape(-1)))
        df2 = max(float(df), 0.5)
        pval = _pchisq(test, df2, lower_tail=False)
        coef_out = np.array([math.nan, math.nan, math.nan, test, df, pval], dtype=float)
        hist_str = " ".join(
            (
                "Variance of random effect=",
                _r_format(theta),
                "  I-likelihood =",
                _r_format(round(clog, 1)),
            )
        )
        return {"coef": coef_out, "history": hist_str}

    return printfun


def _make_pfun() -> Callable[..., dict[str, Any]]:
    def pfun(coef, theta, ndeath):
        coef_arr = np.asarray(coef, dtype=float).reshape(-1)
        if theta == 0:
            return {"recenter": 0.0, "penalty": 0.0, "flag": True}
        recenter = float(np.log(np.mean(np.exp(coef_arr))))
        centered = coef_arr - recenter
        nu = 1.0 / float(theta)
        return {
            "recenter": recenter,
            "first": (np.exp(centered) - 1.0) * nu,
            "second": np.exp(centered) * nu,
            "penalty": float(-np.sum(centered) * nu),
            "flag": False,
        }

    return pfun


def _factorize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[str]]:
    flat = np.asarray(x, dtype=object).reshape(-1)
    mask = np.array(
        [v is None or (isinstance(v, float) and np.isnan(v)) for v in flat],
        dtype=bool,
    )
    present = flat[~mask]
    levels: list[str] = []
    for value in present:
        label = str(value)
        if label not in levels:
            levels.append(label)
    codes = np.empty(flat.size, dtype=float)
    labels = np.empty(flat.size, dtype=object)
    codes[mask] = np.nan
    labels[mask] = None
    for index, value in enumerate(flat):
        if mask[index]:
            continue
        label = str(value)
        codes[index] = float(levels.index(label) + 1)
        labels[index] = label
    return codes, labels, levels


def _r_format(value: float) -> str:
    if math.isnan(value):
        return "NA"
    rounded = float(value)
    if abs(rounded - round(rounded)) < 1e-10:
        return str(int(round(rounded)))
    return f"{rounded:g}"


def _make_aic_cfun(base_cparm: dict[str, Any]):
    def cfun(opt, iter_, old, group, status, loglik, neff, df, plik):
        temp = _frailty_controlaic(opt, iter_, old, neff, df, plik)
        if iter_ > 0:
            theta = float(old["theta"])
            temp = dict(temp)
            temp["c.loglik"] = loglik + _loglik_correction(theta, group, status)
        return temp

    return cfun


def _make_df_cfun():
    def cfun(opt, iter_, old, df_arg, group, status, loglik):
        temp = _frailty_controldf(opt, iter_, old, df_arg)
        if iter_ > 0:
            theta = float(old["theta"])
            temp = dict(temp)
            temp["c.loglik"] = loglik + _loglik_correction(theta, group, status)
        return temp

    return cfun


def frailty_gamma(
    x: Any,
    sparse: Any = _MISSING,
    theta: Any = _MISSING,
    df: Any = _MISSING,
    eps: float = 1e-5,
    method: Any = _MISSING,
    **kwargs: Any,
) -> GammaFrailtyPenalty:
    """Build a gamma frailty penalty term for Cox or survreg models."""
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
            method_val = "df"
        else:
            method_val = "em"

    method_str = str(method_val)
    allowed = ("em", "aic", "df", "fixed")
    if method_str not in allowed:
        raise ValueError(f"'{method_str}' is not a valid method")

    if method_str == "df" and _is_missing(df):
        raise ValueError("Method = df but no df argument")
    if method_str == "fixed" and _is_missing(theta):
        raise ValueError("Method= fixed but no theta argument")
    if method_str != "df" and not _is_missing(df):
        raise ValueError("Method is not df, but have a df argument")
    if method_str != "fixed" and not _is_missing(theta):
        raise ValueError("Method is not 'fixed', but have a theta argument")

    pfun = _make_pfun()
    printfun = _make_printfun()

    if method_str == "fixed":
        cparm = {"theta": float(theta), **kwargs}
        cfun: Callable[..., dict[str, Any]] = _frailty_controlgam
        cargs = ("x", "status", "loglik")
    elif method_str == "em":
        cparm = {"eps": eps, **kwargs}
        cfun = _frailty_controlgam
        cargs = ("x", "status", "loglik")
    elif method_str == "aic":
        cparm = {"eps": eps, "lower": 0.0, "init": np.array([0.1, 1.0]), **kwargs}
        cfun = _make_aic_cfun(cparm)
        cargs = ("x", "status", "loglik", "neff", "df", "plik")
    else:
        df_eps = 0.1 if eps == 1e-5 else eps
        cparm = {
            "df": float(df),
            "thetas": 0.0,
            "dfs": 0.0,
            "eps": df_eps,
            "guess": 3.0 * float(df) / len(codes),
            **kwargs,
        }
        cfun = _make_df_cfun()
        cargs = ("df", "x", "status", "loglik")

    varname: list[str] = []
    if not sparse_flag:
        varname = [f"gamma:{level}" for level in levels]

    return GammaFrailtyPenalty(
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
