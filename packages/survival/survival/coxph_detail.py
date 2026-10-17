"""Detailed Cox partial-likelihood contributions at each event time."""

from __future__ import annotations

import numpy as np

from survival._coxdetail_core import _coxdetail
from survival._coxsurv import _component, _inherits
from survival.cox_zph import _coxph_getdata


def coxph_detail(object, riskmat=False, rorder="data"):
    """Return score and information matrix contributions at each unique event time."""
    method = _component(object, "method")
    if method not in ("breslow", "efron"):
        raise ValueError(
            f"Detailed output is not available for the {method} method"
        )
    if rorder not in ("data", "time"):
        raise ValueError("rorder must be 'data' or 'time'")

    n = len(_component(object, "residuals"))
    temp = _coxph_getdata(object, y=True, x=True, stratax=True, weights=True)
    weights = temp["weights"]
    x = np.asarray(temp["x"], dtype=float)
    y = np.asarray(temp["y"], dtype=float)
    strat = temp["strata"]
    terms = _component(object, "terms")
    if terms is None or not (
        isinstance(terms, dict) or _inherits(terms, "terms")
    ):
        raise ValueError("invalid terms component of object")

    nvar = x.shape[1]
    if y.shape[1] == 2:
        mintime = float(np.min(y[:, 0]))
        if mintime < 0:
            start = np.full(y.shape[0], 2 * mintime - 1, dtype=float)
            y = np.column_stack([start, y])
        else:
            start = np.full(y.shape[0], -1.0, dtype=float)
            y = np.column_stack([start, y])

    if strat is None or len(strat) == 0:
        ord_idx = np.lexsort((-y[:, 2], y[:, 1]))
        newstrat = np.zeros(n, dtype=int)
        newstrat[-1] = 1
    else:
        strat_arr = np.asarray(strat)
        ord_idx = np.lexsort((-y[:, 2], y[:, 1], strat_arr))
        strat_sorted = strat_arr[ord_idx]
        newstrat = np.zeros(n, dtype=int)
        if n > 1:
            newstrat[:-1] = (strat_sorted[:-1] != strat_sorted[1:]).astype(int)
        newstrat[-1] = 1

    xnew = x[ord_idx]
    ynew = y[ord_idx]
    score = np.exp(np.asarray(_component(object, "linear.predictors"), dtype=float))[
        ord_idx
    ]
    if weights is None:
        weights = np.ones(n, dtype=float)
    else:
        weights = np.asarray(weights, dtype=float)[ord_idx]

    ndeath = int(np.sum(y[:, 2]))
    center = np.asarray(_component(object, "means"), dtype=float)
    method_efron = 1.0 if method == "efron" else 0.0

    ff = _coxdetail(
        n,
        nvar,
        ndeath,
        center,
        ynew,
        xnew,
        newstrat,
        score,
        weights,
        method_efron,
        bool(riskmat),
    )
    keep = slice(None, ff["ndeath"])

    time = ynew[ff["index"][keep] - 1, 1]
    means = ff["means"][keep]
    score_out = ff["u"][keep]
    var = ff["var"][keep]

    if riskmat:
        rmat = np.zeros((n, ff["ndeath"]), dtype=float)
        rmat[:, :] = ff["rmat"].T

    out: dict = {
        "time": time,
        "means": means,
        "nevent": ff["nevent"][keep],
        "nrisk": ff["nrisk"][keep],
        "hazard": ff["hazard"][keep],
        "score": score_out,
        "imat": var,
        "varhaz": ff["varhaz"][keep],
        "wtrisk": ff["nrisk2"][keep],
    }

    if rorder == "data":
        out["y"] = y
        out["x"] = x
    else:
        out["y"] = ynew
        out["x"] = xnew

    if strat is not None and len(strat) > 0:
        strat_ord = np.asarray(strat)[ord_idx]
        idx_at_death = ff["index"][keep] - 1
        out["strata"] = {
            str(k): int(v)
            for k, v in zip(
                *np.unique(strat_ord[idx_at_death], return_counts=True)
            )
        }

    if riskmat:
        if rorder == "data":
            risk_data = np.zeros_like(rmat)
            risk_data[ord_idx] = rmat
            out["riskmat"] = risk_data
        else:
            out["riskmat"] = rmat
            out["sortorder"] = ord_idx

    if not np.all(weights == 1):
        out["weights"] = weights
        out["nevent.wt"] = ff["event2"][keep]
        out["nrisk.wt"] = ff["nrisk2"][keep]

    return out
