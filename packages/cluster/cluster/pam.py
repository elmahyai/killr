"""Partitioning around medoids, from ``src/pam.c`` (the original build and swap)."""

from __future__ import annotations

import math

import numpy as np

from cluster._dist import as_matrix, dysta, ind_2, missing_code, prepare_diss, stand_matrix

_EPS = 2.220446049250313e-16


def _bswap(kk, n, nrepr, med_given, do_swap, dys, s):
    s = s * 1.1 + 1.0
    dysma = [0.0] * (n + 1)
    dysmb = [0.0] * (n + 1)
    for i in range(1, n + 1):
        dysma[i] = s
    if med_given:
        for i in range(1, n + 1):
            if nrepr[i] == 1:
                for j in range(1, n + 1):
                    ij = ind_2(i, j)
                    if dysma[j] > dys[ij]:
                        dysma[j] = dys[ij]
    else:
        for _k in range(1, kk + 1):
            nmax = -1
            ammax = 0.0
            for i in range(1, n + 1):
                if nrepr[i] == 0:
                    beter = 0.0
                    for j in range(1, n + 1):
                        cmd = dysma[j] - dys[ind_2(i, j)]
                        if cmd > 0.0:
                            beter += cmd
                    if ammax <= beter:
                        ammax = beter
                        nmax = i
            nrepr[nmax] = 1
            for j in range(1, n + 1):
                ij = ind_2(nmax, j)
                if dysma[j] > dys[ij]:
                    dysma[j] = dys[ij]
    sky = 0.0
    for j in range(1, n + 1):
        sky += dysma[j]
    obj0 = sky / n
    if do_swap and (kk > 1 or med_given):
        while True:
            for j in range(1, n + 1):
                dysma[j] = s
                dysmb[j] = s
                for i in range(1, n + 1):
                    if nrepr[i]:
                        ij = ind_2(i, j)
                        if dysma[j] > dys[ij]:
                            dysmb[j] = dysma[j]
                            dysma[j] = dys[ij]
                        elif dysmb[j] > dys[ij]:
                            dysmb[j] = dys[ij]
            dzsky = 1.0
            hbest = nbest = -1
            for h in range(1, n + 1):
                if nrepr[h]:
                    continue
                for i in range(1, n + 1):
                    if not nrepr[i]:
                        continue
                    dz = 0.0
                    for j in range(1, n + 1):
                        hj = ind_2(h, j)
                        ij = ind_2(i, j)
                        if dys[ij] == dysma[j]:
                            small = dys[hj] if dysmb[j] > dys[hj] else dysmb[j]
                            dz += -dysma[j] + small
                        elif dys[hj] < dysma[j]:
                            dz += -dysma[j] + dys[hj]
                    if dzsky > dz:
                        dzsky = dz
                        hbest = h
                        nbest = i
            if dzsky < -16 * _EPS * abs(sky):
                nrepr[hbest] = 1
                nrepr[nbest] = 0
                sky += dzsky
                continue
            break
    obj1 = sky / n
    return obj0, obj1


def _cstat(kk, n, nrepr, dys, s, all_stats):
    ss = s * 1.1 + 1.0
    nsend = [0] * (n + 1)
    for j in range(1, n + 1):
        if nrepr[j] == 0:
            dsmal = ss
            ksmal = -1
            for k in range(1, n + 1):
                if nrepr[k] == 1:
                    kj = ind_2(k, j)
                    if dsmal > dys[kj]:
                        dsmal = dys[kj]
                        ksmal = k
            nsend[j] = ksmal
        else:
            nsend[j] = j
    ncluv = [0] * (n + 1)
    jk = 1
    nplac = nsend[1]
    for j in range(1, n + 1):
        if nsend[j] == nplac:
            ncluv[j] = 1
    for ja in range(2, n + 1):
        nplac = nsend[ja]
        if ncluv[nplac] == 0:
            jk += 1
            for j in range(2, n + 1):
                if nsend[j] == nplac:
                    ncluv[j] = jk
            if jk == kk:
                break
    if not all_stats:
        return ncluv[1:], None, None, None
    radus = [0.0] * (kk + 1)
    damer = [0.0] * (kk + 1)
    avsyl = [0.0] * (kk + 1)
    separ = [0.0] * (kk + 1)
    med = [0] * (kk + 1)
    nisol = [0] * (kk + 1)
    sizes = [0] * (kk + 1)
    for k in range(1, kk + 1):
        ntt = 0
        ttt = 0.0
        radus[k] = -1.0
        m = -1
        for j in range(1, n + 1):
            if ncluv[j] == k:
                ntt += 1
                m = nsend[j]
                djm = dys[ind_2(j, m)]
                ttt += djm
                if radus[k] < djm:
                    radus[k] = djm
        avsyl[k] = ttt / ntt
        med[k] = m
    if kk == 1:
        clusinf = [[float(n), radus[1], avsyl[1], s, 0.0]]
        return ncluv[1:], med[1:], clusinf, [0]
    for k in range(1, kk + 1):
        nelem = []
        for j in range(1, n + 1):
            if ncluv[j] == k:
                nelem.append(j)
        nel = len(nelem)
        sizes[k] = nel
        if nel == 1:
            nvn = nelem[0]
            damer[k] = 0.0
            separ[k] = ss
            for j in range(1, n + 1):
                if j != nvn:
                    mevj = ind_2(nvn, j)
                    if separ[k] > dys[mevj]:
                        separ[k] = dys[mevj]
            nisol[k] = 0
        else:
            dam = -1.0
            sep = ss
            kand = True
            for nvna in nelem:
                aja = -1.0
                ajb = ss
                for jb in range(1, n + 1):
                    jndz = ind_2(nvna, jb)
                    if ncluv[jb] == k:
                        if aja < dys[jndz]:
                            aja = dys[jndz]
                    elif ajb > dys[jndz]:
                        ajb = dys[jndz]
                if kand and aja >= ajb:
                    kand = False
                if dam < aja:
                    dam = aja
                if sep > ajb:
                    sep = ajb
            separ[k] = sep
            damer[k] = dam
            if kand:
                nisol[k] = 1 if dam >= sep else 2
            else:
                nisol[k] = 0
    clusinf = []
    for k in range(1, kk + 1):
        clusinf.append([float(sizes[k]), radus[k], avsyl[k], damer[k], separ[k]])
    return ncluv[1:], med[1:], clusinf, nisol[1:]


def _dark(kk, n, ncluv, dys, s):
    """Silhouette rows ordered as pam stores them, plus the observation index."""
    ttsyl = 0.0
    avsyl = [0.0] * (kk + 1)
    rows = []
    clustering = [0] + list(ncluv)
    for k in range(1, kk + 1):
        nelem = [j for j in range(1, n + 1) if clustering[j] == k]
        ntt = len(nelem)
        if ntt == 0:
            continue
        syl = [0.0] * ntt
        negbr = [-1] * ntt
        for j, nj in enumerate(nelem):
            dysb = s * 1.1 + 1.0
            negbr[j] = -1
            for k_ in range(1, kk + 1):
                if k_ == k:
                    continue
                db = 0.0
                nbb = 0
                for l in range(1, n + 1):
                    if clustering[l] == k_:
                        nbb += 1
                        if l != nj:
                            db += dys[ind_2(nj, l)]
                db /= nbb
                if dysb > db:
                    dysb = db
                    negbr[j] = k_
            if ntt > 1:
                dysa = 0.0
                for nl in nelem:
                    if nj != nl:
                        dysa += dys[ind_2(nj, nl)]
                dysa /= ntt - 1
                if dysa > 0.0:
                    if dysb > 0.0:
                        if dysb > dysa:
                            syl[j] = 1.0 - dysa / dysb
                        elif dysb < dysa:
                            syl[j] = dysb / dysa - 1.0
                        else:
                            syl[j] = 0.0
                        if syl[j] < -1.0:
                            syl[j] = -1.0
                        elif syl[j] > 1.0:
                            syl[j] = 1.0
                    else:
                        syl[j] = -1.0
                elif dysb > 0.0:
                    syl[j] = 1.0
                else:
                    syl[j] = 0.0
            else:
                syl[j] = 0.0
        av = 0.0
        order = []
        pending = syl[:]
        for _j in range(ntt):
            lang = -1
            symax = -2.0
            for l in range(ntt):
                if symax < pending[l]:
                    symax = pending[l]
                    lang = l
            order.append(lang)
            av += symax
            pending[lang] = -3.0
        ttsyl += av
        avsyl[k] = av / ntt
        if ntt == 1:
            rows.append([float(k), float(negbr[0]), 0.0, float(nelem[0])])
        else:
            for lang in order:
                rows.append([float(k), float(negbr[lang]), syl[lang], float(nelem[lang])])
    ttsyl /= n
    return rows, avsyl[1:], ttsyl


def pam(x, k, diss=False, metric="euclidean", medoids=None, stand=False, cluster_only=False, do_swap=True, keep_diss=None, keep_data=None):
    """Partitioning around medoids. ``medoids`` are 1-based initial indices."""
    metric = str(metric)
    if metric not in {"euclidean", "manhattan"}:
        raise ValueError("metric must be euclidean or manhattan")
    data = None
    if diss:
        n, dys = prepare_diss(x)
    else:
        data = as_matrix(x)
        if stand:
            data = stand_matrix(data)
        filled, jtmd, valmd, _missing = missing_code(data)
        ndyst = 2 if metric == "manhattan" else 1
        dys, jhalt = dysta(filled, ndyst, jtmd, valmd)
        if jhalt:
            raise ValueError("No clustering performed, NAs in the computed dissimilarity matrix.")
        n = data.shape[0]
    k = int(k)
    if k < 1 or k >= n:
        raise ValueError("Number of clusters 'k' must be in {1,2, .., n-1}; hence n >= 2")
    nrepr = [0] * (n + 1)
    med_given = medoids is not None
    if med_given:
        meds = [int(v) for v in medoids]
        if len(meds) != k or len(set(meds)) != k or any(v < 1 or v > n for v in meds):
            raise ValueError("'medoids' must be a vector of k distinct indices in 1..n")
        for med in meds:
            nrepr[med] = 1
    s = 0.0
    for value in dys[1:]:
        if s < value:
            s = value
    obj0, obj1 = _bswap(k, n, nrepr, med_given, bool(do_swap), dys, s)
    all_stats = not cluster_only
    clustering, med, clusinf, isol = _cstat(k, n, nrepr, dys, s, all_stats)
    if cluster_only:
        return clustering
    result = {
        "medoids": None if data is None else [data[i - 1].tolist() for i in med],
        "id_med": [int(v) for v in med],
        "clustering": [int(v) for v in clustering],
        "objective": [float(obj0), float(obj1)],
        "isolation": [int(v) for v in isol],
        "clusinfo": clusinf,
        "data": None if data is None else data.tolist(),
    }
    if 1 < k < n:
        rows, avsil, ttsil = _dark(k, n, clustering, dys, s)
        result["silinfo"] = {
            "widths": [[row[0], row[1], row[2]] for row in rows],
            "index": [int(row[3]) for row in rows],
            "clus_avg_widths": [float(v) for v in avsil],
            "avg_width": float(ttsil),
        }
    else:
        result["silinfo"] = None
    return result


def medoids(x, clustering, diss=False, **kwargs):
    """Medoid index of each cluster, in sorted cluster-id order. 1-based."""
    if diss:
        raise ValueError("'diss = TRUE' is not implemented yet")
    data = as_matrix(x)
    labels = [int(v) if float(v) == int(v) else float(v) for v in np.asarray(clustering).reshape(-1)]
    if len(labels) != data.shape[0]:
        raise ValueError("clustering and x have different lengths")
    groups = {}
    for index, label in enumerate(labels, start=1):
        groups.setdefault(label, []).append(index)
    out = []
    for label in sorted(groups):
        rows = groups[label]
        block = data[[i - 1 for i in rows]]
        chosen = pam(block, k=1, diss=False, **kwargs)["id_med"][0]
        out.append(int(rows[chosen - 1]))
    return out
