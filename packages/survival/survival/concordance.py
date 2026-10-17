"""Concordance statistic (survival::concordance)."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from survival._concordance_core import btree, concordance3, concordance5, fastkm1
from survival.surv import Surv, SurvObject, aeqSurv, is_Surv


def _match_arg(value, choices):
    if value in choices:
        return value
    hits = [c for c in choices if c.startswith(str(value))]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"'{value}' should be one of {', '.join(choices)}")


def _surv_array(y: SurvObject) -> np.ndarray:
    return np.asarray(y.columns, dtype=float)


def _risk_index(risk: np.ndarray) -> np.ndarray:
    _, inv = np.unique(risk, return_inverse=True)
    utemp = inv + 1
    layout = btree(int(np.max(utemp)))
    return layout[utemp - 1].astype(int)


def _sort_stop_right(y: np.ndarray, risk: np.ndarray) -> np.ndarray:
    return np.lexsort((risk, y[:, 1], -y[:, 0]))


def _docount(
    y: np.ndarray,
    risk: np.ndarray,
    weights: np.ndarray,
    *,
    timeopt: str = "n",
    ymax=None,
    std_err: bool = True,
    ranks: bool = False,
):
    n = y.shape[0]
    ny = y.shape[1]
    if np.sum(y[:, ny - 1]) == 0:
        empty = np.zeros(6 if std_err else 5, dtype=float)
        return {
            "count": empty,
            "influence": np.zeros((n, 5), dtype=float),
            "resid": None,
        }

    if np.sum(y[:, ny - 1]) < 2:
        timeopt = "n"

    if ny == 2:
        sort_stop = _sort_stop_right(y, risk)
    else:
        sort_stop = np.lexsort((risk, y[:, 2], -y[:, 1]))
        sort_start = np.argsort(-y[:, 0])

    if timeopt == "n":
        deaths = y[:, ny - 1] > 0
        etime = np.sort(np.unique(y[deaths, ny - 2]))
        timewt = np.ones(len(etime), dtype=float)
    else:
        if ny == 2:
            gfit = fastkm1(y[:, :2], weights, sort_stop)
        else:
            raise NotImplementedError("start-stop timewt options require concordance4")
        etime = gfit["etime"]
        total_wt = np.sum(weights)
        if timeopt == "S":
            timewt = total_wt * gfit["S"] / gfit["nrisk"]
        elif timeopt == "S/G":
            timewt = total_wt * gfit["S"] / (gfit["G"] * gfit["nrisk"])
        elif timeopt == "n/G2":
            timewt = 1.0 / gfit["G"] ** 2
        elif timeopt == "I":
            timewt = 1.0 / gfit["nrisk"]
        else:
            timewt = np.ones(len(etime), dtype=float)
        if not np.all(np.isfinite(timewt)):
            raise RuntimeError("program error, notify author")

    if ymax is not None:
        timewt = np.array(timewt, copy=True)
        timewt[etime > ymax] = 0.0

    bindex = _risk_index(np.asarray(risk, dtype=float))
    rev_timewt = timewt[::-1]

    if std_err:
        if ny == 2:
            fit = concordance3(y[:, :2], bindex, weights, rev_timewt, sort_stop, ranks)
        else:
            raise NotImplementedError("start-stop concordance4 not ported")
    else:
        if ny == 2:
            fit = concordance5(y[:, :2], bindex, weights, rev_timewt, sort_stop)
        else:
            raise NotImplementedError("start-stop concordance6 not ported")
    return fit


def _concordancefit(
    y,
    x,
    strata=None,
    weights=None,
    *,
    ymin=None,
    ymax=None,
    timewt="n",
    cluster=None,
    influence=0,
    ranks=False,
    reverse=False,
    timefix=True,
    keepstrata=10,
    std_err=True,
):
    if np.any(np.isnan(x)) or (is_Surv(y) and np.any(np.isnan(_surv_array(y)))):
        return None
    timewt = _match_arg(timewt, ("n", "S", "S/G", "n/G2", "I"))
    if not std_err:
        ranks = False
        influence = 0

    if is_Surv(y):
        if timefix:
            y = aeqSurv(y)
        surv = _surv_array(y)
        ny = surv.shape[1]
        if y.states is not None:
            raise ValueError("concordance not defined for a multi-state outcome")
        if ny == 3 and timewt in ("S/G", "n/G2"):
            raise ValueError(f"{timewt} timewt option not supported for (time1, time2) data")
        if ymin is not None:
            surv[:, ny - 2] = np.maximum(surv[:, ny - 2], ymin)
    else:
        raise TypeError("y must be a Surv object")

    if y.type in ("left", "interval"):
        raise ValueError("left or interval censored data is not supported")
    if y.type in ("mright", "mcounting"):
        raise ValueError("multiple state survival is not supported")

    n = surv.shape[0]
    xmat = np.atleast_2d(np.asarray(x, dtype=float))
    if xmat.shape[0] != n:
        raise ValueError("x and y are not the same length")
    if xmat.shape[0] == 1 and n > 1:
        xmat = xmat.reshape(n, -1)
    nvar = xmat.shape[1]
    if nvar > 1:
        xname = [f"X{i + 1}" for i in range(nvar)]

    if strata is None or len(strata) == 0:
        strata = np.ones(n, dtype=int)
    else:
        strata = np.asarray(strata)
    if len(strata) != n:
        raise ValueError("y and strata are not the same length")

    if weights is None or len(weights) == 0:
        weights = np.ones(n, dtype=float)
    else:
        weights = np.asarray(weights, dtype=float)
        if len(weights) != n:
            raise ValueError("y and weights are not the same length")

    if ymin is not None and np.any(surv[:, ny - 2] < ymin):
        surv[:, ny - 2] = np.maximum(surv[:, ny - 2], ymin)

    ustrat = np.unique(strata)
    nstrat = len(ustrat)
    if not isinstance(keepstrata, (bool, np.bool_)):
        keepstrata = nstrat <= int(keepstrata)
    if nvar > 1 or nstrat == 1:
        keepstrata = False

    ywork = surv.copy()

    def cfun(yb, xb, wts, twopt):
        if xb.shape[1] == 1:
            return _docount(yb, xb[:, 0], wts, timeopt=twopt, ymax=ymax, std_err=std_err, ranks=ranks)
        temp = [_docount(yb, xb[:, i], wts, timeopt=twopt, ymax=ymax, std_err=std_err, ranks=ranks) for i in range(xb.shape[1])]
        counts = np.row_stack([t["count"] for t in temp])
        fit = {"count": counts}
        if std_err:
            infl = np.stack([t["influence"] for t in temp], axis=2)
            fit["influence"] = infl
        if ranks:
            fit["resid"] = np.stack([t["resid"] for t in temp], axis=2)
        return fit

    if nstrat < 2:
        fit = cfun(ywork, xmat, weights, timewt)
    else:
        tfit = []
        for level in ustrat:
            keep = np.where(strata == level)[0]
            tfit.append(cfun(ywork[keep], xmat[keep], weights[keep], timewt))
        temp = np.concatenate([t["count"].ravel() for t in tfit])
        if not keepstrata and nvar == 1:
            fit = {"count": temp.reshape(-1, 6).sum(axis=0)}
        else:
            fit = {"count": temp.reshape(-1, 6)}
        if std_err or influence > 0:
            if nvar == 1:
                infl = np.zeros((n, 5))
                for level, tf in zip(ustrat, tfit):
                    infl[strata == level] = tf["influence"]
            else:
                infl = np.zeros((n, 5, nvar))
                for level, tf in zip(ustrat, tfit):
                    infl[strata == level] = tf["influence"]
            fit["influence"] = infl

    cname = ["concordant", "discordant", "tied.x", "tied.y", "tied.xy"]
    if nvar > 1:
        npair = np.sum(fit["count"][:, :3], axis=1)
        somer = (fit["count"][:, 0] - fit["count"][:, 1]) / npair
        coxvar = fit["count"][:, 5] / (4 * npair**2)
        rval = {
            "concordance": (somer + 1) / 2,
            "count": fit["count"][:, :5],
            "n": n,
        }
        if std_err or influence in (1, 3) or influence > 3:
            dfbeta = np.zeros((n, nvar))
            for j in range(nvar):
                infl = fit["influence"][:, :, j]
                dfbeta[:, j] = (
                    (infl[:, 0] - infl[:, 1]) - np.sum(infl[:, :3], axis=1) * somer[j]
                ) * weights / (2 * np.repeat(npair[j], n))
            if cluster is not None and len(cluster):
                dfbeta = _rowsum(dfbeta, cluster)
            cvar = dfbeta.T @ dfbeta
        else:
            cvar = None
    else:
        if nstrat > 1 and keepstrata:
            ctemp = fit["count"]
            if ctemp.ndim == 1:
                ctemp = ctemp.reshape(1, -1)
            npair = np.sum(ctemp[:, :3], axis=1)
            somer = (ctemp[:, 0] - ctemp[:, 1]) / npair
            coxvar = ctemp[:, 5] / (4 * npair**2)
            conc = (somer + 1) / 2
            if len(conc) == 1:
                conc = float(conc[0])
            rval = {"concordance": conc, "count": ctemp[:, :5], "n": n}
        else:
            ctemp = fit["count"] if nstrat == 1 else np.sum(fit["count"], axis=0)
            npair = float(np.sum(ctemp[:3]))
            somer = (ctemp[0] - ctemp[1]) / npair
            coxvar = float(ctemp[5]) / (4 * npair**2)
            rval = {
                "concordance": (somer + 1) / 2,
                "count": ctemp[:5],
                "n": n,
            }
            rval["count"] = dict(zip(cname, rval["count"]))

        if std_err or influence in (1, 3):
            infl = fit["influence"]
            dfbeta = ((infl[:, 0] - infl[:, 1]) - np.sum(infl[:, :3], axis=1) * somer) * weights / (2 * npair)
            if cluster is not None and len(cluster):
                dfbeta = _rowsum(dfbeta, cluster)
            cvar = float(np.sum(dfbeta**2))
        else:
            cvar = None

    if std_err and cvar is not None:
        rval["var"] = cvar
        rval["cvar"] = coxvar
    if influence in (1, 3):
        rval["dfbeta"] = dfbeta
    if influence >= 2:
        rval["influence"] = fit["influence"]

    if reverse:
        rval["concordance"] = 1 - rval["concordance"]
        if "dfbeta" in rval:
            rval["dfbeta"] = -rval["dfbeta"]
        cnt = rval["count"]
        if isinstance(cnt, dict):
            keys = list(cnt.keys())
            vals = [cnt[k] for k in keys]
            order = [1, 0, 2, 3, 4]
            rval["count"] = dict(zip(keys, [vals[i] for i in order]))
        elif isinstance(cnt, np.ndarray) and cnt.ndim == 1:
            rval["count"] = cnt[[1, 0, 2, 3, 4]]
    return rval


def _rowsum(values, cluster):
    values = np.asarray(values, dtype=float)
    cluster = np.asarray(cluster)
    out = np.zeros_like(values)
    for label in np.unique(cluster):
        mask = cluster == label
        out[mask] = np.sum(values[mask], axis=0)
    return out if values.ndim > 1 else out.reshape(-1)


def concordance(
    object,
    data: Mapping[str, Any] | None = None,
    *,
    x=None,
    weights=None,
    timewt="n",
    influence=0,
    ranks=False,
    reverse=False,
    timefix=True,
    keepstrata=10,
    ymin=None,
    ymax=None,
    cluster=None,
    **kwargs,
):
    """Compute concordance for a Surv response and predictor(s)."""
    if kwargs:
        raise TypeError(f"unexpected arguments: {', '.join(kwargs)}")

    if x is not None:
        y = object
        if not is_Surv(y):
            raise TypeError("left hand side must be a Surv object when x= is given")
        xarr = np.asarray(x, dtype=float)
        if xarr.ndim == 1:
            xarr = xarr.reshape(-1, 1)
        fit = _concordancefit(
            y,
            xarr,
            weights=weights,
            ymin=ymin,
            ymax=ymax,
            timewt=timewt,
            cluster=cluster,
            influence=influence,
            ranks=ranks,
            reverse=reverse,
            timefix=timefix,
            keepstrata=keepstrata,
        )
        if fit is None:
            return None
        fit["call"] = ("concordance", y, x)
        return fit

    if isinstance(object, str):
        raise NotImplementedError("formula strings require y and x arguments")
    if hasattr(object, "coefficients") and hasattr(object, "call"):
        raise NotImplementedError("concordance for fitted model objects is not translated")
    raise TypeError("concordance expects a Surv response with x= predictor")

