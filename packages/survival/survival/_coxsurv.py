"""Minimal coxph survival curves for basehaz (not exported)."""

from __future__ import annotations

import numpy as np


def _rowsum(x, group):
    x_arr = np.asarray(x, dtype=float)
    if x_arr.ndim == 1:
        x_arr = x_arr.reshape(-1, 1)
    group = np.asarray(group)
    times = np.unique(group)
    out = np.zeros((len(times), x_arr.shape[1]), dtype=float)
    for i, value in enumerate(times):
        out[i] = x_arr[group == value].sum(axis=0)
    if out.shape[1] == 1:
        return out[:, 0]
    return out


def _rcumsum(x):
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        return np.cumsum(arr[::-1])[::-1]
    return np.cumsum(arr[::-1], axis=0)[::-1]


def _agsurv5(n, nvar, dd, x1, x2, xsum, xsum2):
    sum1 = np.zeros(n, dtype=float)
    sum2 = np.zeros(n, dtype=float)
    xbar = np.zeros((n, nvar), dtype=float)
    xsum = np.asarray(xsum, dtype=float)
    xsum2 = np.asarray(xsum2, dtype=float)
    x1 = np.asarray(x1, dtype=float)
    x2 = np.asarray(x2, dtype=float)
    dd = np.asarray(dd, dtype=int)
    for i in range(n):
        d = int(dd[i])
        if d == 1:
            temp = 1.0 / x1[i]
            sum1[i] = temp
            sum2[i] = temp * temp
            for k in range(nvar):
                xbar[i, k] = xsum[i + n * k] * temp * temp
        else:
            temp = 1.0 / x1[i]
            for j in range(d):
                temp = 1.0 / (x1[i] - x2[i] * j / d)
                sum1[i] += temp / d
                sum2[i] += temp * temp / d
                for k in range(nvar):
                    kk = i + n * k
                    xbar[i, k] += ((xsum[kk] - xsum2[kk] * j / d) * temp * temp) / d
    return sum1, sum2, xbar


def _agsurv(y, x, wt, risk, survtype, vartype):
    x_mat = np.atleast_2d(np.asarray(x, dtype=float))
    if x_mat.shape[0] == 1 and x_mat.ndim == 1:
        x_mat = x_mat.reshape(1, -1)
    nvar = x_mat.shape[1]
    y = np.asarray(y, dtype=float)
    status = y[:, y.shape[1] - 1]
    dtime = y[:, y.shape[1] - 2]
    death = status == 1
    time = np.sort(np.unique(dtime))
    nevent = _rowsum(wt * death, dtime)
    ncens = _rowsum(wt * (~death), dtime)
    wrisk = wt * risk
    nrisk = _rcumsum(_rowsum(wrisk, dtime))
    irisk = _rcumsum(_rowsum(wt, dtime))
    if y.shape[1] == 2:
        temp2 = _rowsum(wrisk[:, None] * x_mat, dtime)
        if np.ndim(temp2) == 1:
            xsum = _rcumsum(temp2[:, None])
        else:
            xsum = _rcumsum(temp2)
    else:
        raise NotImplementedError("counting process survival data is not supported")
    ndeath = _rowsum(status, dtime)
    ntime = len(time)
    if survtype == 3 or vartype == 3:
        if nvar:
            xsum2 = _rowsum((wrisk * death)[:, None] * x_mat, dtime)
            if np.ndim(xsum2) == 1:
                xsum2 = xsum2[:, None]
        else:
            xsum2 = np.zeros((len(time), 0))
        erisk = _rowsum(wrisk * death, dtime)
        sum1, sum2, xbar = _agsurv5(
            len(nevent),
            nvar,
            ndeath,
            nrisk,
            erisk,
            xsum.reshape(-1) if nvar else np.array([]),
            xsum2.reshape(-1) if nvar else np.array([]),
        )
    else:
        sum1 = sum2 = xbar = None
    if survtype == 1:
        haz = nevent / nrisk
    elif survtype == 2:
        haz = nevent / nrisk
    else:
        haz = nevent * sum1
    if vartype == 1:
        denom = np.where(nevent >= nrisk, nrisk, nrisk - nevent)
        varhaz = nevent / (nrisk * denom)
        xbar_out = (xsum / nrisk[:, None]) * haz[:, None] if nvar else np.zeros((ntime, 0))
    elif vartype == 2:
        varhaz = nevent / nrisk**2
        xbar_out = (xsum / nrisk[:, None]) * haz[:, None] if nvar else np.zeros((ntime, 0))
    else:
        varhaz = nevent * sum2
        xbar_out = nevent[:, None] * xbar if nvar else np.zeros((ntime, 0))
    return {
        "n": y.shape[0],
        "time": time,
        "n.event": nevent,
        "n.risk": irisk,
        "n.censor": ncens,
        "hazard": haz,
        "cumhaz": np.cumsum(haz),
        "varhaz": varhaz,
        "ndeath": ndeath,
        "xbar": xbar_out,
    }


def _expand_surv(fit, x2, risk2, survtype, se_fit):
    if survtype == 1:
        surv = np.cumprod(fit["surv"]) if "surv" in fit else np.exp(-fit["cumhaz"])
    else:
        surv = np.exp(-fit["cumhaz"])
    x2 = np.asarray(x2, dtype=float)
    if x2.ndim == 1:
        x2 = x2.reshape(1, -1)
    if x2.shape[0] > 1:
        fit = dict(fit)
        fit["surv"] = np.outer(surv, risk2) ** 1  # outer(surv, risk2, '^')
        fit["cumhaz"] = np.outer(fit["cumhaz"], risk2)
    else:
        risk = float(np.asarray(risk2).reshape(-1)[0])
        fit = dict(fit)
        fit["surv"] = surv**risk
        fit["cumhaz"] = fit["cumhaz"] * risk
    if se_fit:
        raise NotImplementedError("se.fit=TRUE is not supported")
    return fit


def coxsurv_fit(ctype, stype, se_fit, y, x, wt, risk, strata=None, x2=None, risk2=1.0):
    if strata is None or len(strata) == 0:
        strata = np.zeros(y.shape[0], dtype=int)
    else:
        strata = np.asarray(strata)
    if wt is None:
        wt = np.ones(y.shape[0], dtype=float)
    else:
        wt = np.asarray(wt, dtype=float)
    risk = np.asarray(risk, dtype=float).reshape(-1)
    x_mat = np.atleast_2d(np.asarray(x, dtype=float))
    if x_mat.shape[0] == 1 and x_mat.size == x_mat.shape[1]:
        x_mat = x_mat.reshape(1, -1)
    survtype = 1 if stype == 1 else ctype + 1
    vartype = survtype
    if isinstance(strata, np.ndarray) and strata.dtype.kind in "iu":
        ustrata = np.sort(np.unique(strata))
    else:
        ustrata = np.sort(np.unique(strata))
    survlist = []
    for level in ustrata:
        indx = np.where(strata == level)[0]
        survlist.append(
            _agsurv(y[indx, :], x_mat[indx, :], wt[indx], risk[indx], survtype, vartype)
        )
    if x2 is None:
        x2 = np.zeros((1, x_mat.shape[1] if x_mat.shape[1] else 1), dtype=float)
    risk2_arr = np.asarray(risk2, dtype=float).reshape(-1)
    expanded = [_expand_surv(item, x2, risk2_arr, survtype, se_fit) for item in survlist]
    if len(expanded) == 1:
        result = expanded[0]
        keep = ("n", "time", "n.risk", "n.event", "n.censor", "surv", "cumhaz")
        return {key: result[key] for key in keep if key in result}
    raise NotImplementedError("stratified coxph models are not supported")


def survfit_coxph(fit, newdata=None, se_fit=False):
    if _inherits(fit, "coxphms"):
        raise ValueError("the basehaz function is not implemented for multi-state models")
    if not _inherits(fit, "coxph"):
        raise ValueError("must be a coxph object")
    y = _component(fit, "y")
    y = np.asarray(y, dtype=float)
    method = _component(fit, "method")
    ctype_map = {"exact": 1, "breslow": 1, "efron": 2}
    ctype = ctype_map.get(str(method), 2)
    stype = 2
    weights = _component(fit, "weights", optional=True)
    means = _component(fit, "means", optional=True)
    coefficients = _component(fit, "coefficients", optional=True)
    if coefficients is None:
        coefficients = np.array([], dtype=float)
    else:
        coefficients = np.asarray(coefficients, dtype=float)
    if means is None or len(means) == 0:
        n = y.shape[0]
        x = np.zeros((n, 1), dtype=float)
        offset_mean = 0.0
        risk = np.ones(n, dtype=float)
        varmat = np.zeros((1, 1), dtype=float)
    else:
        raise NotImplementedError("coxph models with covariates require stored x")
    strata = _component(fit, "strata", optional=True)
    if newdata is not None:
        raise NotImplementedError("newdata is not supported yet")
    risk2 = 1.0
    x2 = np.zeros((1, x.shape[1]), dtype=float)
    return coxsurv_fit(
        ctype,
        stype,
        se_fit,
        y,
        x,
        weights,
        risk,
        strata=strata,
        x2=x2,
        risk2=risk2,
    )


def _inherits(obj, name):
    klass = _component(obj, "class_", optional=True) or _component(obj, "class", optional=True)
    if klass is None:
        klass = getattr(obj, "__class__", None)
        if klass is not None:
            klass = klass.__name__
    if isinstance(klass, str):
        return name in klass.split(".") or klass == name
    if isinstance(klass, (list, tuple)):
        return name in klass
    return False


def _component(obj, name, optional=False):
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
    elif hasattr(obj, name):
        return getattr(obj, name)
    if optional:
        return None
    raise AttributeError(name)
