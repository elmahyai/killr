"""C-level concordance kernels (survival concordance3/4/5/6, fastkm)."""

from __future__ import annotations

import math

import numpy as np


def _walkup(nwt, twt, index: int, ntree: int) -> np.ndarray:
    sums = np.zeros(3, dtype=float)
    sums[2] = nwt[index]
    j = 2 * index + 2
    if j < ntree:
        sums[0] += twt[j]
    if j <= ntree:
        sums[1] += twt[j - 1]
    while index > 0:
        parent = (index - 1) // 2
        if index % 2 == 1:
            sums[0] += twt[parent] - twt[index]
        else:
            sums[1] += twt[parent] - twt[index]
        index = parent
    return sums


def _addin(nwt, twt, index: int, wt: float) -> None:
    nwt[index] += wt
    while index > 0:
        twt[index] += wt
        index = (index - 1) // 2
    twt[0] += wt


def btree(n: int) -> np.ndarray:
    """Binary tree layout from survival::concordance (0-based indices)."""

    def tfun(n_local: int, node_id: int, power: int) -> list[int]:
        if n_local == 1:
            return [node_id]
        if n_local == 2:
            return [2 * node_id + 1, node_id]
        if n_local == 3:
            return [2 * node_id + 1, node_id, 2 * node_id + 2]
        nleft = power if n_local == power * 2 else min(power - 1, n_local - power // 2)
        return (
            tfun(nleft, 2 * node_id + 1, power // 2)
            + [node_id]
            + tfun(n_local - (nleft + 1), 2 * node_id + 2, power // 2)
        )

    if n < 1:
        return np.zeros(0, dtype=int)
    power = int(2 ** math.floor(math.log(n - 1, 2))) if n > 1 else 1
    return np.asarray(tfun(int(n), 0, power), dtype=int)


def concordance3(y, x, wt, timewt, sort_stop, doresid: bool):
    """Right-censored concordance with influence (Cconcordance3)."""
    n = y.shape[0]
    time = y[:, 0]
    status = y[:, 1]
    sort2 = np.asarray(sort_stop, dtype=int)
    x = np.asarray(x, dtype=int)
    wt = np.asarray(wt, dtype=float)
    timewt = np.asarray(timewt, dtype=float)

    ntree = int(np.max(x)) + 1 if n else 0
    nevent = int(np.sum(status))

    nwt = np.zeros(ntree, dtype=float)
    twt = np.zeros(ntree, dtype=float)
    dnwt = np.zeros(ntree, dtype=float)
    dtwt = np.zeros(ntree, dtype=float)

    count = np.zeros(6, dtype=float)
    imat = np.zeros((n, 5), dtype=float)
    resid = np.zeros((nevent, 3), dtype=float) if doresid else None

    z2 = 0.0
    utime = 0
    i = 0
    while i < n:
        ii = sort2[i]
        if status[ii] == 0:
            wsum = _walkup(dnwt, dtwt, x[ii], ntree)
            imat[ii, 0] -= wsum[1]
            imat[ii, 1] -= wsum[0]
            imat[ii, 2] -= wsum[2]
            wsum = _walkup(nwt, twt, x[ii], ntree)
            z2 += wt[ii] * (
                wsum[0] * (wt[ii] + 2 * (wsum[1] + wsum[2]))
                + wsum[1] * (wt[ii] + 2 * (wsum[0] + wsum[2]))
                + (wsum[0] - wsum[1]) ** 2
            )
            _addin(nwt, twt, x[ii], wt[ii])
            i += 1
        else:
            ndeath = 0
            dwt = 0.0
            dwt2 = 0.0
            xsave = x[ii]
            j2 = i
            adjtimewt = timewt[utime]
            utime += 1
            j = i
            while j < n and time[sort2[j]] == time[ii]:
                jj = sort2[j]
                ndeath += 1
                count[3] += wt[jj] * dwt * adjtimewt
                dwt += wt[jj]
                if x[jj] != xsave:
                    if wt[sort2[j2]] < dwt2:
                        for k in range(j2, j):
                            kk = sort2[k]
                            imat[kk, 4] += (dwt2 - wt[kk]) * adjtimewt
                            imat[kk, 3] -= (dwt2 - wt[kk]) * adjtimewt
                    else:
                        j2 = j
                    dwt2 = 0.0
                    xsave = x[jj]
                count[4] += wt[jj] * dwt2 * adjtimewt
                dwt2 += wt[jj]
                wsum = _walkup(nwt, twt, x[jj], ntree)
                for k in range(3):
                    count[k] += wt[jj] * wsum[k] * adjtimewt
                    imat[jj, k] += wsum[k] * adjtimewt
                _addin(dnwt, dtwt, x[jj], adjtimewt * wt[jj])
                j += 1
            if wt[sort2[j2]] < dwt2:
                for k in range(j2, j):
                    kk = sort2[k]
                    imat[kk, 4] += (dwt2 - wt[kk]) * adjtimewt
                    imat[kk, 3] -= (dwt2 - wt[kk]) * adjtimewt
            for k in range(i, i + ndeath):
                jj = sort2[k]
                wsum = _walkup(dnwt, dtwt, x[jj], ntree)
                imat[jj, 0] -= wsum[1]
                imat[jj, 1] -= wsum[0]
                imat[jj, 2] -= wsum[2]
                imat[jj, 3] += (dwt - wt[jj]) * adjtimewt
                wsum = _walkup(nwt, twt, x[jj], ntree)
                z2 += wt[jj] * (
                    wsum[0] * (wt[jj] + 2 * (wsum[1] + wsum[2]))
                    + wsum[1] * (wt[jj] + 2 * (wsum[0] + wsum[2]))
                    + (wsum[0] - wsum[1]) ** 2
                )
                _addin(nwt, twt, x[jj], wt[jj])
            if twt[0] != 0:
                count[5] += dwt * adjtimewt * z2 / twt[0]
            if doresid and resid is not None:
                ne = nevent
                for k in range(i, i + ndeath):
                    jj = sort2[k]
                    wsum = _walkup(nwt, twt, x[jj], ntree)
                    ne -= 1
                    resid[ne, 0] = (wsum[0] - wsum[1]) / twt[0]
                    resid[ne, 1] = twt[0] * adjtimewt
                    resid[ne, 2] = wt[jj]
            i += ndeath

    for i in range(n):
        ii = sort2[i]
        wsum = _walkup(dnwt, dtwt, x[ii], ntree)
        imat[ii, 0] += wsum[1]
        imat[ii, 1] += wsum[0]
        imat[ii, 2] += wsum[2]
    count[3] -= count[4]
    out = {"count": count, "influence": imat}
    if doresid and resid is not None:
        out["resid"] = resid
    return out


def concordance5(y, x, wt, timewt, sort_stop):
    """Concordance counts only (Cconcordance5)."""
    n = y.shape[0]
    time = y[:, 0]
    status = y[:, 1]
    sort2 = np.asarray(sort_stop, dtype=int)
    x = np.asarray(x, dtype=int)
    wt = np.asarray(wt, dtype=float)
    timewt = np.asarray(timewt, dtype=float)

    ntree = int(np.max(x)) + 1 if n else 0
    nwt = np.zeros(ntree, dtype=float)
    twt = np.zeros(ntree, dtype=float)
    count = np.zeros(5, dtype=float)

    utime = 0
    i = 0
    while i < n:
        ii = sort2[i]
        if status[ii] == 0:
            _addin(nwt, twt, x[ii], wt[ii])
            i += 1
        else:
            ndeath = 0
            dwt = 0.0
            dwt2 = 0.0
            xsave = x[ii]
            adjtimewt = timewt[utime]
            utime += 1
            j = i
            while j < n and time[sort2[j]] == time[ii]:
                jj = sort2[j]
                ndeath += 1
                count[3] += wt[jj] * dwt * adjtimewt
                dwt += wt[jj]
                if x[jj] != xsave:
                    dwt2 = 0.0
                    xsave = x[jj]
                count[4] += wt[jj] * dwt2 * adjtimewt
                dwt2 += wt[jj]
                wsum = _walkup(nwt, twt, x[jj], ntree)
                for k in range(3):
                    count[k] += wt[jj] * wsum[k] * adjtimewt
                j += 1
            for k in range(i, i + ndeath):
                jj = sort2[k]
                _addin(nwt, twt, x[jj], wt[jj])
            i += ndeath
    count[3] -= count[4]
    return {"count": count}


def fastkm1(y, wt, sort_stop):
    """Kaplan–Meier at event times for concordance (Cfastkm1)."""
    n = y.shape[0]
    time = y[:, 0]
    status = y[:, 1]
    wt = np.asarray(wt, dtype=float)
    sort = np.asarray(sort_stop, dtype=int)

    dtime = time[sort[0]]
    nevent = 0
    ntemp = 0.0
    dtemp = 0.0
    ctemp = 0.0
    ncount = np.zeros(n, dtype=float)
    dcount = np.zeros(n, dtype=float)
    ccount = np.zeros(n, dtype=float)
    for i in range(n):
        p = sort[i]
        if dtime != time[p]:
            dtemp = 0.0
            ctemp = 0.0
            dtime = time[p]
            if i > 0 and dcount[i - 1] > 0:
                nevent += 1
        ntemp += wt[p]
        if status[p] == 0:
            ctemp += wt[p]
        else:
            dtemp += wt[p]
        ncount[i] = ntemp
        dcount[i] = dtemp
        ccount[i] = ctemp
    if dcount[n - 1] > 0:
        nevent += 1

    s_out = np.zeros(nevent, dtype=float)
    g_out = np.zeros(nevent, dtype=float)
    nrisk_out = np.zeros(nevent, dtype=float)
    etime_out = np.zeros(nevent, dtype=float)

    k = 0
    stemp = 1.0
    gtemp = 1.0
    dfirst = True
    cfirst = True
    dtime = 0.0
    ctime = 0.0
    for i in range(n - 1, -1, -1):
        p = sort[i]
        if status[p] == 1 and (dfirst or time[p] != dtime):
            dtime = time[p]
            dfirst = False
            nrisk_out[k] = ncount[i]
            s_out[k] = stemp
            g_out[k] = gtemp
            etime_out[k] = dtime
            k += 1
            if ncount[i] != 0:
                stemp *= (ncount[i] - dcount[i]) / ncount[i]
        if status[p] == 0 and (cfirst or time[p] != ctime):
            ctime = time[p]
            cfirst = False
            if ncount[i] != 0:
                gtemp *= (ncount[i] - ccount[i]) / ncount[i]
    return {"S": s_out, "G": g_out, "nrisk": nrisk_out, "etime": etime_out}
