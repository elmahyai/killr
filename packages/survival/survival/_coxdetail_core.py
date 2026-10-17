"""Ccoxdetail kernel from survival/src/coxdetail.c."""

from __future__ import annotations

import numpy as np


def _coxdetail(
    nused: int,
    nvar: int,
    ndead_max: int,
    center: np.ndarray,
    y: np.ndarray,
    covar: np.ndarray,
    strata: np.ndarray,
    score: np.ndarray,
    weights: np.ndarray,
    method_efron: float,
    riskmat_flag: bool,
) -> dict:
    """Return per-event means, score, information, hazard pieces, optional risk matrix."""
    start = y[:, 0]
    stop = y[:, 1]
    event = y[:, 2]
    cov = np.array(covar, dtype=float, copy=True)
    for i in range(nvar):
        cov[:, i] -= center[i]

    u = np.zeros((ndead_max, nvar), dtype=float)
    means = np.zeros((ndead_max, nvar), dtype=float)
    var = np.zeros((ndead_max, nvar, nvar), dtype=float)
    rmat = np.zeros((ndead_max, nused), dtype=int) if riskmat_flag else None
    nrisk2 = np.zeros(ndead_max, dtype=float)
    out_start = np.zeros(ndead_max, dtype=float)
    out_stop = np.zeros(ndead_max, dtype=float)
    out_event = np.zeros(ndead_max, dtype=float)
    out_weights = np.zeros(ndead_max, dtype=float)
    out_score = np.zeros(ndead_max, dtype=float)
    out_index = np.zeros(ndead_max, dtype=int)

    a = np.zeros(nvar, dtype=float)
    a2 = np.zeros(nvar, dtype=float)
    cmat = np.zeros((nvar, nvar), dtype=float)
    cmat2 = np.zeros((nvar, nvar), dtype=float)

    ideath = 0
    person = 0
    while person < nused:
        if event[person] == 0:
            person += 1
            continue

        denom = 0.0
        efron_wt = 0.0
        meanwt = 0.0
        a.fill(0.0)
        a2.fill(0.0)
        cmat.fill(0.0)
        cmat2.fill(0.0)
        time = stop[person]
        deaths = 0
        wdeath = 0.0
        nrisk = 0
        for k in range(person, nused):
            if start[k] < time:
                nrisk += 1
                if riskmat_flag:
                    rmat[ideath, k] = 1
                risk = score[k] * weights[k]
                denom += risk
                for i in range(nvar):
                    a[i] += risk * cov[k, i]
                    for j in range(i + 1):
                        cmat[i, j] += risk * cov[k, i] * cov[k, j]
                if stop[k] == time and event[k] == 1:
                    deaths += 1
                    wdeath += weights[k]
                    efron_wt += risk * event[k]
                    meanwt += weights[k]
                    for i in range(nvar):
                        a2[i] += risk * cov[k, i]
                        for j in range(i + 1):
                            cmat2[i, j] += risk * cov[k, i] * cov[k, j]
            if strata[k] == 1:
                break

        itemp = -1
        hazard = 0.0
        varhaz = 0.0
        meanwt /= deaths
        k = person
        while k < nused and stop[k] == time:
            if event[k] == 1:
                itemp += 1
                temp = itemp * method_efron / deaths
                d2 = denom - temp * efron_wt
                hazard += meanwt / d2
                varhaz += meanwt * meanwt / (d2 * d2)
                for i in range(nvar):
                    temp2 = (a[i] - temp * a2[i]) / d2
                    means[ideath, i] += (center[i] + temp2) / deaths
                    u[ideath, i] += weights[k] * cov[k, i] - meanwt * temp2
                    for j in range(i + 1):
                        temp3 = (
                            (cmat[i, j] - temp * cmat2[i, j])
                            - temp2 * (a[j] - temp * a2[j])
                        ) / d2
                        temp3 *= meanwt
                        var[ideath, i, j] += temp3
                        if j < i:
                            var[ideath, j, i] += temp3
            person += 1
            if strata[k] == 1:
                break
            k += 1

        out_index[ideath] = person
        out_score[ideath] = wdeath
        out_start[ideath] = deaths
        out_stop[ideath] = nrisk
        out_event[ideath] = hazard
        out_weights[ideath] = varhaz
        nrisk2[ideath] = denom
        ideath += 1

    ndead = ideath
    return {
        "ndeath": ndead,
        "index": out_index[:ndead],
        "nevent": out_start[:ndead],
        "nrisk": out_stop[:ndead],
        "hazard": out_event[:ndead],
        "varhaz": out_weights[:ndead],
        "event2": out_score[:ndead],
        "nrisk2": nrisk2[:ndead],
        "means": means[:ndead],
        "u": u[:ndead],
        "var": var[:ndead],
        "rmat": rmat[:ndead] if riskmat_flag else None,
    }
