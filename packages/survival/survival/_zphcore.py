"""Czph1 and Czph2 kernels for the proportional hazards test."""

import math

import numpy as np


def _zph1(gtime, y, x, eta, weights, strata, method_efron, sort):
    """Port of survival/src/zph1.c. x is (n, p); sort is 0-based indices."""
    x = np.atleast_2d(np.asarray(x, dtype=float))
    if x.shape[0] == 1 and x.size > 1:
        x = x.T
    nused, nvar = x.shape
    ny = y.shape[1]
    status = y[:, ny - 1]
    xtime = y[:, ny - 2]
    covar = np.array(x, dtype=float, order="C")
    gt = np.asarray(gtime, dtype=float)
    eta = np.asarray(eta, dtype=float)
    weights = np.asarray(weights, dtype=float)
    strata = np.asarray(strata, dtype=int)
    sort = np.asarray(sort, dtype=int)

    nevent = int(np.sum(status == 1))
    nstrat = int(np.max(strata)) + 1 if nused else 1

    u = np.zeros(2 * nvar, dtype=float)
    imat = np.zeros((2 * nvar, 2 * nvar), dtype=float)
    schoen = np.zeros((nevent, nvar), dtype=float)
    used = np.zeros((nstrat, nvar), dtype=int)

    k = 0
    ndead = 0.0
    cstrat = int(strata[sort[0]])
    for i in range(nused):
        person = int(sort[i])
        if cstrat == int(strata[person]):
            ndead += status[person]
        else:
            for j in range(nvar):
                used[cstrat, j] = 0
                for kk in range(k, i):
                    person2 = int(sort[kk])
                    if covar[person2, j] != covar[int(sort[k]), j]:
                        used[cstrat, j] = int(ndead)
                        break
            ndead = status[int(sort[i])]
            k = i
            cstrat = int(strata[int(sort[i])])
    for j in range(nvar):
        used[cstrat, j] = 0
        for kk in range(k, nused):
            person2 = int(sort[kk])
            if covar[person2, j] != covar[int(sort[k]), j]:
                used[cstrat, j] = int(ndead)
                break

    for i in range(nvar):
        tmean = np.mean(covar[:, i])
        covar[:, i] -= tmean

    a = np.zeros(nvar, dtype=float)
    a2 = np.zeros(nvar, dtype=float)
    cmat = np.zeros((nvar, nvar), dtype=float)
    cmat2 = np.zeros((nvar, nvar), dtype=float)

    cstrat = -1
    ip = nused - 1
    nevent_left = nevent
    while ip >= 0:
        person = int(sort[ip])
        if int(strata[person]) != cstrat:
            cstrat = int(strata[person])
            denom = 0.0
            a.fill(0.0)
            cmat.fill(0.0)

        dtime = xtime[person]
        timewt = gt[person]
        ndead_t = 0
        deadwt = 0.0
        denom2 = 0.0

        while ip >= 0:
            person = int(sort[ip])
            if xtime[person] != dtime or int(strata[person]) != cstrat:
                break
            risk = math.exp(eta[person]) * weights[person]
            if status[person] == 0:
                denom += risk
                for ii in range(nvar):
                    a[ii] += risk * covar[person, ii]
                    for jj in range(ii + 1):
                        cmat[ii, jj] += risk * covar[person, ii] * covar[person, jj]
            else:
                ndead_t += 1
                deadwt += weights[person]
                denom2 += risk
                nevent_left -= 1
                for ii in range(nvar):
                    schoen[nevent_left, ii] = covar[person, ii]
                    u[ii] += weights[person] * covar[person, ii]
                    u[ii + nvar] += timewt * weights[person] * covar[person, ii]
                    a2[ii] += risk * covar[person, ii]
                    for jj in range(ii + 1):
                        cmat2[ii, jj] += risk * covar[person, ii] * covar[person, jj]
            ip -= 1

        if ndead_t > 0:
            if not method_efron:
                denom += denom2
                for ii in range(nvar):
                    a[ii] += a2[ii]
                    temp2 = a[ii] / denom
                    u[ii] -= deadwt * temp2
                    u[ii + nvar] -= timewt * deadwt * temp2
                    for jj in range(ii + 1):
                        cmat[ii, jj] += cmat2[ii, jj]
                        temp = deadwt * (cmat[ii, jj] - temp2 * a[jj]) / denom
                        imat[jj, ii] += temp
                        imat[jj, ii + nvar] += temp * timewt
                        imat[jj + nvar, ii + nvar] += temp * timewt * timewt
                    for j in range(ndead_t):
                        schoen[nevent_left + j, ii] -= temp2
            else:
                wtave = deadwt / ndead_t
                for ii in range(nvar):
                    tmean = 0.0
                    for k_ef in range(ndead_t):
                        temp = (k_ef + 1) / ndead_t
                        tmean += (a[ii] + a2[ii] * temp) / (denom + denom2 * temp)
                    for j in range(ndead_t):
                        schoen[nevent_left + j, ii] -= tmean / ndead_t
                for k_ef in range(ndead_t):
                    denom += denom2 / ndead_t
                    for ii in range(nvar):
                        a[ii] += a2[ii] / ndead_t
                        temp2 = a[ii] / denom
                        u[ii] -= wtave * temp2
                        u[ii + nvar] -= timewt * wtave * temp2
                        for jj in range(ii + 1):
                            cmat[ii, jj] += cmat2[ii, jj] / ndead_t
                            temp = wtave * (cmat[ii, jj] - temp2 * a[jj]) / denom
                            imat[jj, ii] += temp
                            imat[jj, ii + nvar] += temp * timewt
                            imat[jj + nvar, ii + nvar] += temp * timewt * timewt
            a2.fill(0.0)
            cmat2.fill(0.0)

    for ii in range(nvar):
        for jj in range(ii):
            imat[ii, jj] = imat[jj, ii]
            imat[ii, jj + nvar] = imat[jj, ii + nvar]
            imat[ii + nvar, jj + nvar] = imat[jj + nvar, ii + nvar]
    for ii in range(nvar):
        for jj in range(nvar):
            imat[ii + nvar, jj] = imat[jj, ii + nvar]

    return {"u": u, "imat": imat, "schoen": schoen, "used": used}


def _zph2(gtime, y, x, eta, weights, strata, method_efron, sort1, sort2):
    """Port of survival/src/zph2.c for start-stop data."""
    x = np.atleast_2d(np.asarray(x, dtype=float))
    if x.shape[0] == 1 and x.size > 1:
        x = x.T
    nused, nvar = x.shape
    start = y[:, 0]
    tstop = y[:, 1]
    status = y[:, 2]
    covar = np.array(x, dtype=float, order="C")
    gt = np.asarray(gtime, dtype=float)
    eta = np.asarray(eta, dtype=float)
    weights = np.asarray(weights, dtype=float)
    strata = np.asarray(strata, dtype=int)
    sort1 = np.asarray(sort1, dtype=int)
    sort2 = np.asarray(sort2, dtype=int)

    nevent = int(np.sum(status == 1))
    nstrat = int(np.max(strata)) + 1 if nused else 1

    u = np.zeros(2 * nvar, dtype=float)
    imat = np.zeros((2 * nvar, 2 * nvar), dtype=float)
    schoen = np.zeros((nevent, nvar), dtype=float)
    used = np.zeros((nstrat, nvar), dtype=int)
    keep = np.zeros(nused, dtype=int)

    a = np.zeros(nvar, dtype=float)
    a2 = np.zeros(nvar, dtype=float)
    cmat = np.zeros((nvar, nvar), dtype=float)
    cmat2 = np.zeros((nvar, nvar), dtype=float)

    k = 0
    ndead = 0.0
    cstrat = int(strata[sort2[0]])
    for i in range(nused):
        person = int(sort2[i])
        if cstrat == int(strata[person]):
            ndead += status[person]
        else:
            p1 = int(sort2[k])
            for j in range(nvar):
                used[cstrat, j] = 0
                for kk in range(k, i):
                    person2 = int(sort2[kk])
                    if covar[person2, j] != covar[p1, j]:
                        used[cstrat, j] = int(ndead)
                        break
            k = i
            ndead = status[int(sort2[i])]
            cstrat = int(strata[int(sort2[i])])
    p1 = int(sort2[k])
    for j in range(nvar):
        used[cstrat, j] = 0
        for kk in range(k, nused):
            person2 = int(sort2[kk])
            if covar[person2, j] != covar[p1, j]:
                used[cstrat, j] = int(ndead)
                break

    for i in range(nvar):
        tmean = np.mean(covar[:, i])
        covar[:, i] -= tmean

    person = 0
    indx1 = 0
    denom = 0.0
    nrisk = 0
    etasum = 0.0
    cstrat = -1
    recenter = 0.0
    nevent_left = nevent

    while person < nused:
        dtime = None
        timewt = 1.0
        for k2 in range(person, nused):
            if int(strata[sort2[k2]]) != cstrat:
                cstrat = int(strata[sort2[k2]])
                denom = 0.0
                nrisk = 0
                etasum = 0.0
                a.fill(0.0)
                cmat.fill(0.0)
                person = k2
                indx1 = k2
            p = int(sort2[k2])
            if status[p] == 1:
                dtime = tstop[p]
                timewt = gt[p]
                break
        if dtime is None:
            person = nused
            continue

        while indx1 < nused:
            p1 = int(sort1[indx1])
            if int(strata[p1]) != cstrat or start[p1] < dtime:
                break
            if keep[p1] == 0:
                indx1 += 1
                continue
            nrisk -= 1
            if nrisk == 0:
                etasum = 0.0
                denom = 0.0
                a.fill(0.0)
                cmat.fill(0.0)
            else:
                etasum -= eta[p1]
                risk = math.exp(eta[p1] - recenter) * weights[p1]
                denom -= risk
                for ii in range(nvar):
                    a[ii] -= risk * covar[p1, ii]
                    for jj in range(ii + 1):
                        cmat[ii, jj] -= risk * covar[p1, ii] * covar[p1, jj]
            indx1 += 1

        denom2 = 0.0
        ndead_t = 0
        meanwt = 0.0
        a2.fill(0.0)
        cmat2.fill(0.0)

        while person < nused:
            p = int(sort2[person])
            if int(strata[p]) != cstrat or tstop[p] < dtime:
                break
            etasum += eta[p]
            nrisk += 1
            if abs(etasum / nrisk - recenter) > 200:
                temp = etasum / nrisk - recenter
                recenter = etasum / nrisk
                if denom > 0:
                    if abs(temp) > 709:
                        raise OverflowError("exp overflow due to covariates")
                    temp = math.exp(-temp)
                    denom *= temp
                    for ii in range(nvar):
                        a[ii] *= temp
                        for jj in range(nvar):
                            cmat[ii, jj] *= temp
            risk = math.exp(eta[p] - recenter) * weights[p]
            if status[p] == 1:
                nevent_left -= 1
                keep[p] = 1
                ndead_t += 1
                denom2 += risk
                meanwt += weights[p]
                for ii in range(nvar):
                    u[ii] += weights[p] * covar[p, ii]
                    u[ii + nvar] += weights[p] * covar[p, ii] * timewt
                    a2[ii] += risk * covar[p, ii]
                    schoen[nevent_left, ii] = covar[p, ii]
                    for jj in range(ii + 1):
                        cmat2[ii, jj] += risk * covar[p, ii] * covar[p, jj]
            elif start[p] < dtime:
                keep[p] = 1
                denom += risk
                for ii in range(nvar):
                    a[ii] += risk * covar[p, ii]
                    for jj in range(ii + 1):
                        cmat[ii, jj] += risk * covar[p, ii] * covar[p, jj]
            person += 1

        if ndead_t > 0:
            if not method_efron or ndead_t == 1:
                denom += denom2
                for ii in range(nvar):
                    a[ii] += a2[ii]
                    temp = a[ii] / denom
                    u[ii] -= meanwt * temp
                    u[ii + nvar] -= meanwt * temp * timewt
                    for jj in range(ii + 1):
                        cmat[ii, jj] += cmat2[ii, jj]
                        temp2 = meanwt * ((cmat[ii, jj] - temp * a[jj]) / denom)
                        imat[jj, ii] += temp2
                        imat[jj, ii + nvar] += temp2 * timewt
                        imat[jj + nvar, ii + nvar] += temp2 * timewt * timewt
                    for j in range(ndead_t):
                        schoen[nevent_left + j, ii] -= temp
            else:
                meanwt /= ndead_t
                for ii in range(nvar):
                    tmean = 0.0
                    for k_ef in range(ndead_t):
                        temp = (k_ef + 1) / ndead_t
                        tmean += (a[ii] + a2[ii] * temp) / (denom + denom2 * temp)
                    for j in range(ndead_t):
                        schoen[nevent_left + j, ii] -= tmean / ndead_t
                for k_ef in range(ndead_t):
                    denom += denom2 / ndead_t
                    for ii in range(nvar):
                        a[ii] += a2[ii] / ndead_t
                        temp = a[ii] / denom
                        u[ii] -= meanwt * temp
                        u[ii + nvar] -= meanwt * temp * timewt
                        for jj in range(ii + 1):
                            cmat[ii, jj] += cmat2[ii, jj] / ndead_t
                            temp2 = meanwt * ((cmat[ii, jj] - temp * a[jj]) / denom)
                            imat[jj, ii] += temp2
                            imat[jj, ii + nvar] += temp2 * timewt
                            imat[jj + nvar, ii + nvar] += temp2 * timewt * timewt
            if nrisk > 0 and abs(etasum / nrisk) > 200:
                temp = etasum / nrisk
                eta = eta - temp
                temp = math.exp(-temp)
                denom *= temp
                for ii in range(nvar):
                    a[ii] *= temp
                    for jj in range(nvar):
                        cmat[ii, jj] *= temp
                etasum = 0.0

    for ii in range(nvar):
        for jj in range(ii):
            imat[ii, jj] = imat[jj, ii]
            imat[ii, jj + nvar] = imat[jj, ii + nvar]
            imat[ii + nvar, jj + nvar] = imat[jj + nvar, ii + nvar]
    for ii in range(nvar):
        for jj in range(nvar):
            imat[ii + nvar, jj] = imat[jj, ii + nvar]

    return {"u": u, "imat": imat, "schoen": schoen, "used": used}
