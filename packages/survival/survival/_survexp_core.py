"""pyears3b kernel from survival/src/pyears3b.c (expected survival)."""

from __future__ import annotations

import numpy as np


def _pystep(nc, data, fac, dims, cuts, step, edge):
    """pystep from survival/src/pystep.c (for-loop index matches C)."""
    index = 0
    index2 = 0
    wt = 1.0
    shortfall = 0.0
    maxtime = step
    kk = 1
    for i in range(nc):
        if fac[i] == 1:
            index += int(data[i] - 1) * kk
        else:
            if fac[i] > 1:
                dtemp = 1 + (fac[i] - 1) * dims[i]
            else:
                dtemp = dims[i]
            j = 0
            while True:
                if j >= dtemp:
                    j = dtemp
                    break
                if data[i] < cuts[i][j]:
                    break
                j += 1
            if j == 0:
                temp = cuts[i][j] - data[i]
                if edge == 0 and temp > shortfall:
                    shortfall = min(step, temp)
                if temp < maxtime:
                    maxtime = temp
            elif j == dtemp:
                if edge == 0:
                    temp = cuts[i][j] - data[i]
                    if temp <= 0:
                        shortfall = step
                    elif temp < maxtime:
                        maxtime = temp
                if fac[i] > 1:
                    j = dims[i] - 1
                else:
                    j -= 1
            else:
                temp = cuts[i][j] - data[i]
                if temp < maxtime:
                    maxtime = temp
                j -= 1
                if fac[i] > 1:
                    wt = 1.0 - (j % fac[i]) / float(fac[i])
                    j //= fac[i]
                    index2 = kk
            index += j * kk
        kk *= dims[i]
    index2 += index
    if shortfall == 0:
        return maxtime, index, index2, wt
    return shortfall, -1, index2, wt


def _build_ecut(efac: np.ndarray, edims: np.ndarray, ecut_flat: np.ndarray) -> list[np.ndarray]:
    ecut: list[np.ndarray] = []
    pos = 0
    flat = np.asarray(ecut_flat, dtype=float).reshape(-1)
    for i in range(len(edims)):
        if efac[i] == 0:
            ecut.append(flat[pos : pos + edims[i]])
            pos += int(edims[i])
        elif efac[i] > 1:
            span = 1 + int((efac[i] - 1) * edims[i])
            ecut.append(flat[pos : pos + span])
            pos += span
        else:
            ecut.append(np.asarray([], dtype=float))
    return ecut


def pyears3b(
    death: bool,
    efac: np.ndarray,
    edims: np.ndarray,
    ecut_flat: np.ndarray,
    expect: np.ndarray,
    grpx: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    times: np.ndarray,
    ngrp: int,
) -> dict[str, np.ndarray]:
    """Person-years kernel for cohort expected survival (Cpyears3b)."""
    death_flag = 1 if death else 0
    efac = np.asarray(efac, dtype=int).reshape(-1)
    edims = np.asarray(edims, dtype=int).reshape(-1)
    edim = len(edims)
    expect = np.asarray(expect, dtype=float).reshape(-1)
    grpx = np.asarray(grpx, dtype=int).reshape(-1)
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    times = np.sort(np.unique(np.asarray(times, dtype=float).reshape(-1)))
    ntime = times.size
    n = y.size
    ecut = _build_ecut(efac, edims, ecut_flat)

    esurv = np.zeros(ntime * ngrp, dtype=float)
    nsurv = np.zeros(ntime * ngrp, dtype=int)
    wvec = np.zeros(ntime * ngrp, dtype=float)

    data2 = np.zeros(edim, dtype=float)
    for i in range(n):
        cumhaz = 0.0
        for j in range(edim):
            data2[j] = x[i, j]
        timeleft = float(y[i])
        group = int(grpx[i]) - 1
        time = 0.0
        for j in range(ntime):
            if timeleft <= 0:
                break
            thiscell = float(times[j] - time)
            if thiscell > timeleft:
                thiscell = timeleft
            index = j + ntime * group
            etime = thiscell
            hazard = 0.0
            while etime > 0:
                et2, indx, indx2, wt = _pystep(edim, data2, efac, edims, ecut, etime, 1)
                if et2 <= 0:
                    break
                if wt < 1:
                    hazard += et2 * (wt * expect[indx] + (1.0 - wt) * expect[indx2])
                else:
                    hazard += et2 * expect[indx]
                for k in range(edim):
                    if efac[k] != 1:
                        data2[k] += et2
                etime -= et2
            if times[j] == 0:
                wvec[index] = 1.0
                if death_flag == 0:
                    esurv[index] = 1.0
                else:
                    esurv[index] = 0.0
            elif death_flag == 0:
                esurv[index] += np.exp(-(cumhaz + hazard)) * thiscell
                wvec[index] += np.exp(-cumhaz) * thiscell
            else:
                esurv[index] += hazard * thiscell
                wvec[index] += thiscell
            nsurv[index] += 1
            cumhaz += hazard
            time += thiscell
            timeleft -= thiscell

    for i in range(ntime * ngrp):
        if wvec[i] > 0:
            if death_flag == 0:
                esurv[i] /= wvec[i]
            else:
                esurv[i] = np.exp(-esurv[i] / wvec[i])
        elif death_flag != 0:
            esurv[i] = np.exp(-esurv[i])

    return {"surv": esurv, "n": nsurv, "ntime": ntime, "ngrp": ngrp}


def survexp_fit(
    group: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    times: np.ndarray,
    death: bool,
    ratetable: dict,
) -> dict[str, np.ndarray]:
    """R survexp.fit: expected survival curves for matched ratetable indices."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 2:
        raise ValueError("x must be a matrix")
    dim_rt = len(ratetable["dim"])
    if x.shape[1] != dim_rt:
        raise ValueError("x matrix does not match the rate table")
    times = np.sort(np.unique(np.asarray(times, dtype=float).reshape(-1)))
    if np.any(times < 0):
        raise ValueError("Negative time point requested")
    if y is None or (isinstance(y, float) and np.isnan(y)):
        y = np.full(x.shape[0], float(np.max(times)))
    y = np.asarray(y, dtype=float).reshape(-1)
    ntime = times.size
    ngrp = int(np.max(group))

    atts = ratetable
    cuts = []
    for cp in atts["cutpoints"]:
        if cp is not None and not (hasattr(cp, "__len__") and len(cp) == 0):
            cuts.append(cp)
        else:
            cuts.append(None)

    if atts.get("type") is None:
        rfac = np.asarray(atts["factor"], dtype=int)
        us_special = rfac > 1
    else:
        rtype = np.asarray(atts["type"], dtype=int)
        rfac = (rtype == 1).astype(int)
        us_special = rtype == 4

    xwork = np.array(x, dtype=float, copy=True)
    if np.any(us_special):
        dimid = list(atts.get("dimid") or atts.get("dimnames_names") or [])
        try:
            cols = [dimid.index("age"), dimid.index("year")]
        except ValueError as exc:
            raise ValueError("ratetable does not have expected shape") from exc
        bdate = xwork[:, cols[1]] - xwork[:, cols[0]]
        byear = np.floor(bdate / 365.25)
        offset = bdate - byear * 365.25
        xwork[:, cols[1]] = xwork[:, cols[1]] - offset
        if np.any(rfac > 1):
            temp = int(np.where(us_special)[0][0])
            nyear = len(cuts[temp])
            nint = int(rfac[temp])
            xs = nint * np.arange(1, nyear + 1, dtype=float)
            ys = np.asarray(cuts[temp], dtype=float)
            xout = np.arange(nint, nint * nyear + 1, dtype=float)
            cuts[temp] = np.round(np.interp(xout, xs, ys) - 0.0001)

    efac = rfac
    edims = np.asarray(atts["dim"], dtype=int)
    ecut_parts = []
    for i, dim in enumerate(edims):
        if efac[i] == 0:
            cp = cuts[i]
            if cp is None:
                ecut_parts.append(np.arange(1, int(dim) + 1, dtype=float))
            else:
                ecut_parts.append(np.asarray(cp, dtype=float).reshape(-1))
        elif efac[i] > 1:
            cp = cuts[i]
            if cp is None:
                raise ValueError("missing cutpoints for interpolated dimension")
            cp = np.asarray(cp, dtype=float).reshape(-1)
            ecut_parts.append(cp)
        else:
            ecut_parts.append(np.asarray([], dtype=float))
    ecut_flat = np.concatenate([p.reshape(-1) for p in ecut_parts]) if ecut_parts else np.asarray([], dtype=float)

    temp = pyears3b(
        death=death,
        efac=efac,
        edims=edims,
        ecut_flat=ecut_flat,
        expect=np.asarray(atts["data"], dtype=float),
        grpx=np.asarray(group, dtype=int),
        x=xwork,
        y=y,
        times=times,
        ngrp=ngrp,
    )
    surv = temp["surv"]
    n_out = temp["n"]
    if ntime == 1:
        return {"surv": surv, "n": n_out}
    if ngrp > 1:
        mat = surv.reshape(ntime, ngrp, order="F")
        nmat = n_out.reshape(ntime, ngrp, order="F")
        return {
            "surv": np.apply_along_axis(lambda col: np.cumprod(col), 0, mat),
            "n": nmat,
        }
    return {"surv": np.cumprod(surv), "n": n_out}
