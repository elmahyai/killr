"""Penalized parametric survreg fit (survival::survpenal.fit).

The R front end runs here: argument checks, the starting values from the
intercept-only fit (Csurvreg6, through ``survival.survreg_fit``), the penalty term
bookkeeping, and the list that R returns. The Newton-Raphson loop, the penalty
updates, the golden-section step halving, the outer loop with the penalty control
functions, and ``coxpenal.df`` run in the survreg7 crate (Csurvreg7, survpenal.c,
survregc1.c, coxpenal.df).

Scope, as in the crate: built-in distributions only (extreme value, logistic,
Gaussian), dense penalties with a diagonal penalty matrix (ridge-style terms), and
no sparse frailty term. Other inputs raise ``NotImplementedError``.

Penalty terms are objects with the attributes R keeps on a ``coxph.penalty`` term:
``pfun``, ``cfun``, ``cparm``, ``pparm``, ``cargs``, ``diag``, and ``sparse``
(``survival.ridge.RidgePenalty`` has all of them). ``pcols`` and ``assign`` use the
1-based column numbers that R and ``attrassign`` use.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
from survreg7 import survpenal_fit as _crate_survpenal_fit

from survival.control import survreg_control
from survival.survreg_fit import _derfun, _kernel, _resolve_dist


def _as_terms(value: Any) -> list[list[int]]:
    if value is None:
        return []
    if isinstance(value, dict):
        value = list(value.values())
    return [[int(v) for v in np.atleast_1d(group)] for group in value]


def _cargs_list(cargs: Any) -> list[str]:
    if cargs is None:
        return []
    if isinstance(cargs, str):
        return [cargs]
    return [str(c) for c in cargs]


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def survpenal_fit(
    x,
    y,
    weights=None,
    offset=None,
    init=None,
    controlvals=None,
    dist="extreme",
    scale=0,
    nstrat=1,
    strata=None,
    pcols=None,
    pattr=None,
    assign=None,
    parms=None,
):
    """Fit a penalized survreg model for the matrix ``x`` and response ``y``.

    ``y`` has two columns (time, status) or three (time1, time2, status), as in
    ``Surv``. ``pcols`` lists the 1-based X columns of each penalized term, ``pattr``
    the penalty objects in the same order, and ``assign`` the 1-based column groups
    of each model term. The return value is a dict with the field names of the R
    list: ``coefficients``, ``icoef``, ``var``, ``var2``, ``loglik``, ``iter``,
    ``linear.predictors``, ``df``, ``df2``, ``penalty``, ``pterms``, ``assign2``,
    ``history``, ``printfun``, and ``score``.
    """
    if controlvals is None:
        controlvals = survreg_control()
    iter_max = controlvals["iter.max"]
    outer_max = controlvals["outer.max"]
    eps = controlvals["rel.tolerance"]
    toler_chol = controlvals["toler.chol"]

    x = np.array(x, dtype=float, copy=True)
    if x.ndim != 2:
        raise ValueError("Invalid X matrix ")
    n, nvar = x.shape
    y = np.asarray(y, dtype=float)
    if y.ndim != 2:
        raise ValueError("y must be a matrix")
    ny = y.shape[1]
    if ny < 2:
        raise ValueError("y must have a time and a status column")

    if offset is None:
        offset = np.zeros(n)
    else:
        offset = np.asarray(offset, dtype=float)
    if weights is None:
        weights = np.ones(n)
    else:
        weights = np.asarray(weights, dtype=float)
        if np.any(weights <= 0):
            raise ValueError("Invalid weights, must be >0")

    if scale < 0:
        raise ValueError("Invalid scale")
    if scale > 0 and nstrat > 1:
        raise ValueError("Cannot have both a fixed scale and strata")
    if nstrat > 1 and (strata is None or np.size(strata) != n):
        raise ValueError("Invalid strata variable")
    if nstrat == 1:
        strata = np.ones(n, dtype=np.int32)
    else:
        strata = np.asarray(strata, dtype=np.int32)
    nstrat2 = 0 if scale > 0 else nstrat
    nvar2 = nvar + nstrat2
    if nvar2 == 0:
        raise ValueError(
            "Cannot fit a model with no coefficients other than sparse ones"
        )

    sd, dnum = _resolve_dist(dist)
    density = sd["density"]

    def derfun(eta, sigma):
        return _derfun(y, eta, sigma, density, parms)

    status = y[:, ny - 1]
    if pattr is None:
        pattr = []
    if pcols is None:
        pcols = []
    npenal = len(pattr)
    if npenal == 0 or len(pcols) != npenal:
        raise ValueError("Invalid pcols or pattr arg")
    sparse = [bool(_attr(p, "sparse", False)) for p in pattr]
    if sum(sparse) > 1:
        raise ValueError("Only one sparse penalty term allowed")
    if any(sparse):
        raise NotImplementedError(
            "sparse (frailty) penalty terms are not in the survreg7 crate"
        )
    diag = [bool(_attr(p, "diag", True)) for p in pattr]
    if not all(diag):
        raise NotImplementedError(
            "penalties with a full (non-diagonal) penalty matrix are not in the survreg7 crate"
        )

    assign_terms = _as_terms(assign)
    # Mark each penalized term's position in assign, and keep the penalties in term order.
    pcols_1 = [[int(c) for c in np.atleast_1d(group)] for group in pcols]
    pindex = []
    for i in range(npenal):
        match = [k for k, term in enumerate(assign_terms) if term == pcols_1[i]]
        if not match:
            raise ValueError("pcols and assign arguments disagree")
        pindex.append(match[0])
    pterms = np.zeros(len(assign_terms), dtype=int)
    for k in pindex:
        pterms[k] = 1
    if int(np.sum(pterms > 0)) != npenal:
        raise ValueError("pcols and assign arguments disagree")
    order = sorted(range(npenal), key=lambda i: pindex[i])
    if order != list(range(npenal)):
        pindex = [pindex[i] for i in order]
        pcols_1 = [pcols_1[i] for i in order]
        pattr = [pattr[i] for i in order]

    # The scale columns are appended to assign when they are estimated.
    assign_ext = [list(term) for term in assign_terms]
    if nstrat2 > 0:
        assign_ext.append(list(range(nvar + 1, nvar2 + 1)))

    # Starting values: the intercept-only fit with the mean shifted (survpenal.fit).
    yy = np.where(status != 3, y[:, 0], (y[:, 0] + y[:, 1]) / 2.0)
    coef = np.asarray(sd["init"](yy, weights, parms), dtype=float)
    if scale > 0:
        vars_ = math.log(scale)
    else:
        vars_ = math.log(4.0 * coef[1]) / 2.0
    coef = np.concatenate(([coef[0]], np.repeat(vars_, nstrat)))
    dg, ddg = derfun(yy, math.exp(vars_))
    wt = -1.0 * ddg * weights
    coef[0] = np.sum(weights * dg + wt * (yy - offset)) / np.sum(wt)

    fit0 = _kernel(
        20,
        1,
        y,
        ny,
        np.ones((n, 1)),
        weights,
        offset,
        coef,
        nstrat2,
        strata,
        eps,
        toler_chol,
        dnum,
    )

    # The effective n of the model.
    temp = float(np.mean(np.exp(fit0["coef"][1:])))
    k0 = 1 + nstrat2
    var0 = np.asarray(fit0["var"], dtype=float).reshape((k0, k0), order="F")
    n_eff = float(sd["variance"](temp**2) * np.linalg.inv(var0)[0, 0])

    if init is not None:
        init = np.asarray(init, dtype=float)
        if init.size == nvar:
            if scale > 0:
                init = np.concatenate([init, [math.log(scale)]])
            else:
                init = np.concatenate([init, fit0["coef"][1:]])
        elif init.size != nvar2:
            raise ValueError("Wrong length for inital values")
        if scale > 0:
            init = np.concatenate([init, [math.log(scale)]])
    else:
        init = np.concatenate(
            [[fit0["coef"][0]], np.zeros(nvar - 1), fit0["coef"][1:]]
        )

    penalties = []
    for i, p in enumerate(pattr):
        cparm = dict(_attr(p, "cparm", {}) or {})
        cparm["eps2"] = math.sqrt(eps)
        pparm = _attr(p, "pparm", None)
        extra = None if pparm is None else np.asarray(pparm, dtype=float)
        penalties.append(
            (
                [c - 1 for c in pcols_1[i]],
                _attr(p, "pfun"),
                _attr(p, "cfun"),
                cparm,
                _cargs_list(_attr(p, "cargs", None)),
                extra,
            )
        )

    out = _crate_survpenal_fit(
        np.asfortranarray(x).ravel(order="F"),
        nvar,
        np.asfortranarray(y).ravel(order="F"),
        ny,
        np.ascontiguousarray(weights, dtype=np.float64),
        np.ascontiguousarray(offset, dtype=np.float64),
        np.ascontiguousarray(strata, dtype=np.int32),
        np.ascontiguousarray(init, dtype=np.float64),
        nstrat2,
        dnum,
        n_eff,
        float(eps),
        float(toler_chol),
        int(iter_max),
        int(outer_max),
        [[k - 1 for k in term] for term in assign_ext],
        [int(k) for k in pindex],
        penalties,
    )

    if iter_max > 1 and out["iterfail"]:
        warnings.warn(
            "Inner loop failed to coverge for iterations "
            + " ".join(str(i) for i in out["iterfail"])
        )

    coef_fit = np.asarray(out["coef"], dtype=float).copy()
    hdiag = np.asarray(out["hdiag"], dtype=float)
    which_sing = np.flatnonzero(hdiag[:nvar] == 0)
    coef_fit[which_sing] = np.nan

    var = np.asarray(out["var"], dtype=float).reshape((nvar2, nvar2), order="F")
    var2 = np.asarray(out["var2"], dtype=float).reshape((nvar2, nvar2), order="F")
    linear_predictors = x @ coef_fit[:nvar]

    return {
        "coefficients": coef_fit,
        "icoef": fit0["coef"].copy(),
        "var": var,
        "var2": var2,
        "loglik": np.array([fit0["loglik"], out["loglik"] - out["penalty"]]),
        "iter": np.array([out["iter_outer"], out["iter_total"]]),
        "linear.predictors": linear_predictors,
        "df": np.asarray(out["df"], dtype=float),
        "df2": None,
        "penalty": np.array([0.0, -out["penalty"]]),
        "pterms": pterms,
        "assign2": [list(term) for term in assign_ext],
        "history": out["iterlist"],
        "printfun": [_attr(p, "printfun", None) for p in pattr],
        "score": np.asarray(out["u"], dtype=float),
    }
