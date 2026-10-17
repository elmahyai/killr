"""Test proportional hazards for a Cox model fit."""

from __future__ import annotations

import math
from collections import OrderedDict

import numpy as np

from survival._coxsurv import _component, _inherits
from survival._zphcore import _zph1, _zph2
from survival.gamma import _pgamma_raw


def _pchisq(q, df, *, lower_tail=False):
    if math.isnan(q) or math.isnan(df) or df <= 0:
        return math.nan
    if df == 1:
        root = math.sqrt(max(float(q), 0.0))
        pnorm = 0.5 * (1.0 + math.erf(root / math.sqrt(2.0)))
        upper = 2.0 * (1.0 - pnorm)
        return 1.0 - upper if lower_tail else upper
    shape = df / 2.0
    x = q / 2.0
    cdf = _pgamma_raw(x, shape)
    if lower_tail:
        return cdf
    return 1.0 - cdf


def _coxph_getdata(fit, *, y=True, x=True, stratax=True, weights=True):
    ty = fit.get("y") if isinstance(fit, dict) else _component(fit, "y", optional=True)
    tx = fit.get("x") if isinstance(fit, dict) else _component(fit, "x", optional=True)
    twt = fit.get("weights") if isinstance(fit, dict) else _component(fit, "weights", optional=True)
    if ty is not None:
        n = ty.shape[0]
    elif tx is not None:
        n = tx.shape[0]
    else:
        raise ValueError("fit has no y or x")
    if twt is None:
        twt = np.ones(n, dtype=float)
    strat = None
    if stratax:
        strat = fit.get("strata") if isinstance(fit, dict) else _component(fit, "strata", optional=True)
    return {"y": ty, "x": tx, "weights": np.asarray(twt, dtype=float), "strata": strat}


def _km_transform(y, times):
    """Left-continuous KM transform used by cox.zph with transform='km'."""
    ny = y.shape[1]
    xtime = y[:, ny - 2]
    status = y[:, ny - 1]
    order = np.argsort(xtime, kind="mergesort")
    t = xtime[order]
    s = status[order]
    tvec = []
    surv = []
    surv_val = 1.0
    i = 0
    n = t.size
    while i < n:
        ti = t[i]
        nd = 0
        j = i
        while j < n and t[j] == ti:
            if s[j] == 1:
                nd += 1
            j += 1
        nr = n - i
        if nd > 0:
            surv_val *= 1.0 - nd / nr
            tvec.append(ti)
            surv.append(surv_val)
        i = j
    if not tvec:
        return np.zeros_like(times, dtype=float)
    tvec = np.array(tvec, dtype=float)
    surv = np.array(surv, dtype=float)
    padded = np.concatenate([[1.0], surv])
    indx = np.searchsorted(tvec, times, side="right") - 1
    return 1.0 - padded[np.maximum(indx, 0)]


def _as_assign_list(asgn):
    if isinstance(asgn, OrderedDict):
        return asgn
    if isinstance(asgn, dict):
        return OrderedDict(asgn)
    raise ValueError("assign must be a mapping")


def cox_zph(fit, transform="km", terms=True, singledf=False, global_=True):
    """Score test of proportional hazards for a coxph fit object."""
    if not (_inherits(fit, "coxph") or _inherits(fit, "coxme")):
        raise ValueError("argument must be the result of a coxph or coxme fit")
    if _inherits(fit, "coxph.null"):
        raise ValueError("there are no score residuals for a Null model")
    terms_obj = _component(fit, "terms", optional=True)
    if terms_obj is not None:
        specials = terms_obj.get("specials", {}) if isinstance(terms_obj, dict) else getattr(terms_obj, "specials", {})
        if specials and specials.get("tt"):
            raise ValueError("function not defined for models with tt() terms")

    if _inherits(fit, "coxme"):
        raise NotImplementedError("coxme models are not supported")

    cget = _coxph_getdata(fit, y=True, x=True, stratax=True, weights=True)
    y = np.asarray(cget["y"], dtype=float)
    ny = y.shape[1]
    event = y[:, ny - 1] == 1
    if cget["strata"] is not None and len(cget["strata"]) > 0:
        istrat = np.asarray(cget["strata"], dtype=int) - 1
    else:
        istrat = np.zeros(y.shape[0], dtype=int)

    if not terms:
        singledf = False

    lp = np.asarray(_component(fit, "linear.predictors"), dtype=float)
    eta = lp - np.mean(lp)
    x = np.asarray(cget["x"], dtype=float)

    coefficients = np.asarray(_component(fit, "coefficients"), dtype=float)
    varnames = list(_component(fit, "coefficients").keys()) if isinstance(_component(fit, "coefficients"), dict) else None
    if varnames is None:
        names_attr = getattr(_component(fit, "coefficients"), "names", None)
        if names_attr is not None:
            varnames = list(names_attr)
        else:
            varnames = [f"x{i}" for i in range(coefficients.size)]
    nvar = len(varnames)

    if not terms:
        asgn = OrderedDict((name, [i + 1]) for i, name in enumerate(varnames))
    elif _inherits(fit, "coxphms"):
        raise NotImplementedError("multi-state coxph models are not supported")
    else:
        asgn = _as_assign_list(_component(fit, "assign"))

    frail_keys = [
        k
        for k in asgn
        if "frailty(" in k or "frailty.gamma(" in k or "frailty.gaussian(" in k
    ]
    if frail_keys:
        dcol = []
        for k in frail_keys:
            dcol.extend(asgn[k])
        dcol0 = sorted({c - 1 for c in dcol})
        x = np.delete(x, dcol0, axis=1)
        for k in frail_keys:
            del asgn[k]

    fcoef = coefficients.copy()
    if np.any(np.isnan(fcoef)):
        keep = ~np.isnan(fcoef)
        varnames = [v for v, k in zip(varnames, keep) if k]
        x = x[:, keep]
        fcoef = fcoef[keep]
        new = []
        for cols in asgn.values():
            new.extend(cols)
        new_keep = [c for c in new if keep[c - 1]]
        new_asgn = OrderedDict()
        for name, cols in asgn.items():
            mapped = [new_keep.index(c) + 1 for c in cols if c in new_keep]
            if mapped:
                new_asgn[name] = mapped
        asgn = new_asgn
        nvar = len(new_keep)

    termname = list(asgn.keys())
    nterm = len(asgn)

    times = y[:, ny - 2]
    if isinstance(transform, str):
        tname = transform
        if transform == "identity":
            ttimes = times.copy()
        elif transform == "rank":
            ttimes = np.argsort(np.argsort(times)) + 1.0
        elif transform == "log":
            ttimes = np.log(times)
        elif transform == "km":
            ttimes = _km_transform(y, times)
        else:
            raise ValueError("Unrecognized transform")
    else:
        tname = "user"
        ttimes = np.asarray(transform(times), dtype=float)

    gtime = ttimes - np.mean(ttimes[event])
    method = _component(fit, "method")
    method_efron = method == "efron" if isinstance(method, str) else bool(method)

    if ny == 2:
        ord_idx = np.lexsort((y[:, 0], istrat))
        resid = _zph1(gtime, y, x, eta, cget["weights"], istrat, method_efron, ord_idx)
    else:
        ord1 = np.lexsort((-y[:, 0], -istrat))
        ord2 = np.lexsort((-y[:, 1], -istrat))
        resid = _zph2(gtime, y, x, eta, cget["weights"], istrat, method_efron, ord1, ord2)

    test = np.zeros(nterm + 1, dtype=float)
    df = np.ones(nterm + 1, dtype=int)
    u0 = np.zeros(nvar, dtype=float)

    coxlist2 = _component(fit, "coxlist2", optional=True)
    if coxlist2 is not None:
        pmat = np.zeros((2 * nvar, 2 * nvar), dtype=float)
        tmat = np.asarray(coxlist2["second"], dtype=float)
        if np.any(np.isnan(coefficients)):
            keep = ~np.isnan(coefficients)
            tmat = tmat[np.ix_(keep, keep)]
        pmat[:nvar, :nvar] = tmat
        pmat[nvar:, nvar:] = tmat
        imatr = resid["imat"] + pmat
    else:
        imatr = resid["imat"]

    fit_df = _component(fit, "df", optional=True)

    for ii, (term, jj) in enumerate(asgn.items(), start=1):
        jj0 = [j - 1 for j in jj]
        kk = list(range(nvar)) + [j + nvar for j in jj0]
        imat = imatr[np.ix_(kk, kk)]
        u = np.concatenate([u0, resid["u"][np.array(jj0) + nvar]])
        if singledf and len(jj) > 1:
            vv = np.linalg.inv(imat)[nvar:, nvar:]
            t1 = float(np.sum(fcoef[jj0] * resid["u"][np.array(jj0) + nvar]))
            test[ii - 1] = t1 * t1 * float(fcoef[jj0] @ vv @ fcoef[jj0])
            df[ii - 1] = 1
        else:
            test[ii - 1] = float(u @ np.linalg.solve(imat, u))
            if fit_df is None:
                df[ii - 1] = len(jj)
            else:
                df[ii - 1] = int(np.asarray(fit_df)[ii - 1])

    if global_:
        u = np.concatenate([u0, resid["u"][nvar:]])
        test[nterm] = float(u @ np.linalg.solve(imatr, u))
        if fit_df is None:
            df[nterm] = nvar
        else:
            df[nterm] = int(np.sum(fit_df))
        tbl = np.column_stack([test, df.astype(float), [_pchisq(t, d) for t, d in zip(test, df)]])
        rownames = termname + ["GLOBAL"]
    else:
        tbl = np.column_stack(
            [test[:nterm], df[:nterm].astype(float), [_pchisq(t, d) for t, d in zip(test[:nterm], df[:nterm])]]
        )
        rownames = termname

    if ny == 2:
        indx = ord_idx
    else:
        indx = ord2[::-1]
    indx = indx[event[indx]]
    rval = {
        "table": {"rownames": rownames, "colnames": ["chisq", "df", "p"], "data": tbl},
        "x": ttimes[indx].copy(),
        "time": y[indx, ny - 2].copy(),
        "transform": tname,
    }
    if cget["strata"] is not None and len(cget["strata"]) > 0:
        rval["strata"] = np.asarray(cget["strata"])[indx]

    used = resid["used"].astype(float)
    for cols in asgn.values():
        if len(cols) > 1:
            jj = [c - 1 for c in cols]
            if np.any(used[:, jj] == 0):
                used[:, jj] = np.max(used[:, jj], axis=1, keepdims=True)

    wtmat = np.zeros((nvar, nvar), dtype=float)
    for i in range(used.shape[0]):
        row = used[i, :]
        wtmat += np.minimum.outer(row, row)

    vmean = imatr[:nvar, :nvar].copy()
    mask = wtmat == 0
    vmean = np.divide(vmean, np.where(mask, 1.0, wtmat), where=~mask, out=vmean)
    vmean[mask] = imatr[:nvar, :nvar][mask]

    sresid = np.array(resid["schoen"], dtype=float, copy=True)
    if terms and any(len(v) > 1 for v in asgn.values()):
        temp = np.zeros((sresid.shape[1], nterm), dtype=float)
        for i, (term, j) in enumerate(asgn.items()):
            jj = [c - 1 for c in j]
            if len(jj) == 1:
                temp[jj[0], i] = 1.0
            else:
                temp[jj, i] = fcoef[jj]
        sresid = sresid @ temp
        vmean = temp.T @ vmean @ temp
        used = used[:, [list(asgn.values())[i][0] - 1 for i in range(nterm)]]

    sgrp = np.repeat(np.arange(used.shape[0]), np.max(used, axis=1).astype(int))
    for i in range(used.shape[0]):
        k = np.where(used[i, :] > 0)[0]
        if k.size == 0:
            continue
        j = np.where(sgrp == i)[0]
        if k.size == 1:
            sresid[j, k[0]] /= vmean[k[0], k[0]]
        else:
            sresid[j[:, None], k] = np.linalg.solve(vmean[np.ix_(k, k)], sresid[j[:, None], k].T).T
        other = np.setdiff1d(np.arange(sresid.shape[1]), k)
        if other.size:
            sresid[np.ix_(j, other)] = np.nan

    for i, (term, j) in enumerate(asgn.items()):
        jj = [c - 1 for c in j]
        if len(jj) == 1:
            sresid[:, i] += fcoef[jj[0]]
        else:
            sresid[:, i] += 1.0

    rval["y"] = sresid
    rval["var"] = np.linalg.inv(vmean)
    rval["class_"] = ("cox.zph",)
    return rval
