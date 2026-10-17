"""Agglomerative nesting and divisive analysis, from ``src/twins.c``."""

from __future__ import annotations

import math

import numpy as np

from cluster._dist import as_matrix, dysta, ind_2, missing_code, prepare_diss, stand_matrix

_METHODS = ("average", "single", "complete", "ward", "weighted", "flexible", "gaverage")


def _pmatch(name, choices):
    text = str(name)
    exact = [item for item in choices if item == text]
    if len(exact) == 1:
        return exact[0]
    hits = [item for item in choices if item.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ValueError("invalid clustering method")
    raise ValueError("ambiguous clustering method")


def bncoef(height):
    """Agglomerative or divisive coefficient from a banner of heights."""
    ban = [0.0] + [float(v) for v in height]
    n = len(ban)
    n_1 = n - 1
    sup = 0.0
    for k in range(1, n):
        if sup < ban[k]:
            sup = ban[k]
    cf = 0.0
    k = 0
    while k < n:
        kearl = k if k > 0 else 1
        k += 1
        kafte = k if k < n else n_1
        syze = min(ban[kearl], ban[kafte])
        cf += 1.0 - syze / sup
    return cf / n


def coef_hier(object):
    """Coefficient from an agnes, diana, or hclust height vector."""
    height = object["height"] if isinstance(object, dict) else object.height
    if len(height) < 1:
        raise ValueError("height is empty")
    return bncoef(height)


def coef_hclust(object):
    """Agglomerative coefficient from an hclust merge matrix and its heights."""
    height = np.asarray(object["height"] if isinstance(object, dict) else object.height, dtype=float)
    merge = np.asarray(object["merge"] if isinstance(object, dict) else object.merge, dtype=float)
    nh = int(height.shape[0])
    if nh < 1 or merge.shape != (nh, 2):
        raise ValueError("invalid hclust object")
    if np.any(np.diff(height) < 0):
        raise ValueError("height is not sorted")
    leaves = np.sum(merge < 0, axis=1)
    return float(1.0 - np.sum(leaves * height) / np.max(height) / (nh + 1))


def _merge_matrix(flat, n_1):
    rows = []
    for i in range(n_1):
        rows.append([int(flat[i]), int(flat[i + n_1])])
    return rows


def _par_method(method, par_method):
    if method == "flexible":
        if par_method is None:
            raise ValueError("'par.method' must be of length 1, 3, or 4")
        values = [float(v) for v in np.atleast_1d(np.asarray(par_method, dtype=float)).reshape(-1)]
        if len(values) == 1:
            a = values[0]
            return [0.0, a, a, 1 - 2 * a, 0.0]
        if len(values) == 3:
            return [0.0, values[0], values[1], values[2], 0.0]
        if len(values) == 4:
            return [0.0] + values
        raise ValueError("'par.method' must be of length 1, 3, or 4")
    if method == "gaverage":
        if par_method is None:
            beta = -0.1
            return [0.0, 1 - beta, 1 - beta, beta, 0.0]
        values = [float(v) for v in np.atleast_1d(np.asarray(par_method, dtype=float)).reshape(-1)]
        if len(values) == 1:
            b = values[0]
            return [0.0, 1 - b, 1 - b, b, 0.0]
        if len(values) == 3:
            return [0.0, values[0], values[1], values[2], 0.0]
        if len(values) == 4:
            return [0.0] + values
        raise ValueError("'par.method' must be of length 1, 3, or 4")
    return [0.0, 0.0]


def _agnes_c(nn, dys, method, alpha):
    kwan = [0] * (nn + 1)
    ner = [0] * (nn + 1)
    ban = [0.0] * (nn + 1)
    n_1 = nn - 1
    merge = [0] * (2 * n_1)
    flex = method in (6, 7)
    has_a3 = flex and alpha[3] != 0.0
    has_a4 = flex and alpha[4] != 0.0

    def mget(i, j):
        return merge[i if j == 1 else i + n_1]

    def mset(i, j, value):
        merge[i if j == 1 else i + n_1] = value

    for j in range(1, nn + 1):
        kwan[j] = 1
        ner[j] = j

    for nmerge in range(n_1):
        j = 1
        while True:
            j += 1
            if kwan[j] != 0:
                break
        d_min = dys[ind_2(1, j)] * 1.1 + 1.0
        la = lb = -1
        for k in range(1, n_1 + 1):
            if kwan[k] <= 0:
                continue
            for j in range(k + 1, nn + 1):
                if kwan[j] <= 0:
                    continue
                k_j = ind_2(k, j)
                if d_min >= dys[k_j]:
                    d_min = dys[k_j]
                    la = k
                    lb = j
        l1 = -la
        l2 = -lb
        for j in range(nmerge):
            if mget(j, 1) == l1 or mget(j, 2) == l1:
                l1 = j + 1
            if mget(j, 1) == l2 or mget(j, 2) == l2:
                l2 = j + 1
        mset(nmerge, 1, l1)
        mset(nmerge, 2, l2)
        if flex and l1 == l2:
            raise ValueError("agnes lead to invalid merge")
        llast = lfyrs = -1
        for k in range(1, nn + 1):
            if ner[k] == la:
                lfyrs = k
            if ner[k] == lb:
                llast = k
        ban[llast] = d_min
        if lfyrs + kwan[la] != llast:
            lput = lfyrs + kwan[la]
            lenda = llast + kwan[lb] - 2
            for _k in range(1, llast - lput + 1):
                lka = ner[lput]
                akb = ban[lput]
                for j in range(lput, lenda + 1):
                    ner[j] = ner[j + 1]
                    ban[j] = ban[j + 1]
                ner[lenda + 1] = lka
                ban[lenda + 1] = akb
        for lq in range(1, nn + 1):
            if lq == la or lq == lb or kwan[lq] == 0:
                continue
            naq = ind_2(la, lq)
            nbq = ind_2(lb, lq)
            if method == 1:
                ta = float(kwan[la])
                tb = float(kwan[lb])
                dys[naq] = (ta / (ta + tb)) * dys[naq] + (tb / (ta + tb)) * dys[nbq]
            elif method == 2:
                dys[naq] = dys[naq] if dys[naq] < dys[nbq] else dys[nbq]
            elif method == 3:
                dys[naq] = dys[naq] if dys[naq] > dys[nbq] else dys[nbq]
            elif method == 4:
                ta = float(kwan[la])
                tb = float(kwan[lb])
                tq = float(kwan[lq])
                fa = (ta + tq) / (ta + tb + tq)
                fb = (tb + tq) / (ta + tb + tq)
                fc = -tq / (ta + tb + tq)
                nab = ind_2(la, lb)
                inside = fa * dys[naq] * dys[naq] + fb * dys[nbq] * dys[nbq] + fc * dys[nab] * dys[nab]
                dys[naq] = math.sqrt(inside) if inside >= 0.0 else float("nan")
            elif method == 5:
                dys[naq] = (dys[naq] + dys[nbq]) / 2.0
            elif method == 6:
                d_new = alpha[1] * dys[naq] + alpha[2] * dys[nbq]
                if has_a3:
                    d_new += alpha[3] * dys[ind_2(la, lb)]
                if has_a4:
                    d_new += alpha[4] * abs(dys[naq] - dys[nbq])
                dys[naq] = d_new
            elif method == 7:
                ta = float(kwan[la])
                tb = float(kwan[lb])
                fa = alpha[1] * ta / (ta + tb)
                fb = alpha[2] * tb / (ta + tb)
                d_new = fa * dys[naq] + fb * dys[nbq]
                if has_a3:
                    d_new += alpha[3] * dys[ind_2(la, lb)]
                if has_a4:
                    d_new += alpha[4] * abs(dys[naq] - dys[nbq])
                dys[naq] = d_new
            else:
                raise ValueError(f"invalid method (code {method})")
        kwan[la] += kwan[lb]
        kwan[lb] = 0
    return ner[1:], ban, _merge_matrix(merge, n_1)


def _min_dis(dys, ka, kb, ner):
    dm = 0.0
    for k in range(ka - 1, kb - 1):
        ner_k = ner[k + 1]
        for j in range(k + 1, kb):
            k_j = ind_2(ner_k, ner[j + 1])
            if dm < dys[k_j]:
                dm = dys[k_j]
    return dm


def _splyt(nn, dys):
    kwan = [0] * (nn + 1)
    ner = [0] * (nn + 1)
    ban = [0.0] * (nn + 1)
    n_1 = nn - 1
    nclu = 1
    nhalf = nn * n_1 // 2 + 1
    for l in range(1, nn + 1):
        ner[l] = l
    kwan[1] = nn
    ja = 1
    cs = 0.0
    for k in range(nhalf):
        if cs < dys[k]:
            cs = dys[k]
    label = "L30"
    while label != "done":
        if label == "L30":
            jb = ja + kwan[ja] - 1
            jma = jb
            if kwan[ja] == 2:
                kwan[ja] = 1
                kwan[jb] = 1
                ban[jb] = dys[ind_2(ner[ja], ner[jb])]
            else:
                bygsd = -1.0
                lndsd = -1
                for l in range(ja, jb + 1):
                    lner = ner[l]
                    sd = 0.0
                    for j in range(ja, jb + 1):
                        sd += dys[ind_2(lner, ner[j])]
                    if bygsd < sd:
                        bygsd = sd
                        lndsd = l
                kwan[ja] -= 1
                kwan[jb] = 1
                if jb != lndsd:
                    lchan = ner[lndsd]
                    lmm = jb - 1
                    for lmma in range(lndsd, lmm + 1):
                        ner[lmma] = ner[lmma + 1]
                    ner[jb] = lchan
                splyn = 0
                jma = jb - 1
                while True:
                    splyn += 1
                    rest = jma - ja
                    jaway = -1
                    bdyff = -1.0
                    for l in range(ja, jma + 1):
                        lner = ner[l]
                        da = 0.0
                        db = 0.0
                        for j in range(ja, jma + 1):
                            da += dys[ind_2(lner, ner[j])]
                        da /= rest
                        for j in range(jma + 1, jb + 1):
                            db += dys[ind_2(lner, ner[j])]
                        db /= splyn
                        dyff = da - db
                        if bdyff < dyff:
                            bdyff = dyff
                            jaway = l
                    jmb = jma + 1
                    if bdyff <= 0.0:
                        break
                    if jma != jaway:
                        lchan = ner[jaway]
                        lmz = jma - 1
                        for lxx in range(jaway, lmz + 1):
                            ner[lxx] = ner[lxx + 1]
                        ner[jma] = lchan
                    for lxx in range(jmb, jb + 1):
                        l_1 = lxx - 1
                        if ner[l_1] < ner[lxx]:
                            break
                        lchan = ner[l_1]
                        ner[l_1] = ner[lxx]
                        ner[lxx] = lchan
                    kwan[ja] -= 1
                    kwan[jma] = kwan[jmb] + 1
                    kwan[jmb] = 0
                    jma -= 1
                    jmb = jma + 1
                    if jma == ja:
                        break
                if ner[ja] >= ner[jmb]:
                    lxxa = ja
                    for lgrb in range(jmb, jb + 1):
                        lxxa += 1
                        lchan = ner[lgrb]
                        lxg = -1
                        for ll in range(lxxa, lgrb + 1):
                            lxf = lgrb - ll + lxxa
                            lxg = lxf - 1
                            ner[lxf] = ner[lxg]
                        ner[lxg] = lchan
                    llq = kwan[jmb]
                    kwan[jmb] = 0
                    jma = ja + jb - jma - 1
                    jmb = jma + 1
                    kwan[jmb] = kwan[ja]
                    kwan[ja] = llq
                if nclu == 1:
                    ban[jmb] = cs
                else:
                    ban[jmb] = _min_dis(dys, ja, jb, ner)
            nclu += 1
            if nclu < nn:
                if jb != nn:
                    label = "L420"
                else:
                    label = "reset"
            else:
                label = "done"
            continue
        if label == "L420":
            ja += kwan[ja]
            if ja <= nn:
                if kwan[ja] <= 1:
                    continue
                label = "L30"
                continue
            label = "reset"
            continue
        ja = 1
        if kwan[ja] == 1:
            label = "L420"
        else:
            label = "L30"

    merge = [0] * (2 * n_1)

    def mget(i, j):
        return merge[i if j == 1 else i + n_1]

    def mset(i, j, value):
        merge[i if j == 1 else i + n_1] = value

    for nmerge in range(n_1):
        nj = -1
        dmin = cs
        for j in range(2, nn + 1):
            if kwan[j] >= 0 and dmin >= ban[j]:
                dmin = ban[j]
                nj = j
        kwan[nj] = -1
        l1 = -ner[nj - 1]
        l2 = -ner[nj]
        for j in range(nmerge):
            if mget(j, 1) == l1 or mget(j, 2) == l1:
                l1 = j + 1
            if mget(j, 1) == l2 or mget(j, 2) == l2:
                l2 = j + 1
        mset(nmerge, 1, l1)
        mset(nmerge, 2, l2)
    return ner[1:], ban, _merge_matrix(merge, n_1), cs


def _distances(x, diss, metric, stand):
    if diss:
        n, dys = prepare_diss(x)
        data = None
        return n, dys, data
    data = as_matrix(x)
    if stand:
        data = stand_matrix(data)
    filled, jtmd, valmd, _missing = missing_code(data)
    ndyst = 2 if str(metric) == "manhattan" else 1
    dys, jhalt = dysta(filled, ndyst, jtmd, valmd)
    if jhalt:
        raise ValueError("No clustering performed, NA-values in the dissimilarity matrix.")
    return data.shape[0], dys, data


def agnes(x, diss=False, metric="euclidean", stand=False, method="average", par_method=None, keep_diss=None, keep_data=None):
    """Agglomerative nesting. Returns order, height, ac, and merge."""
    method_name = _pmatch(method, _METHODS)
    code = _METHODS.index(method_name) + 1
    alpha = _par_method(method_name, par_method)
    n, dys, data = _distances(x, diss, metric, stand)
    if n <= 1:
        raise ValueError("need at least 2 objects to cluster")
    order, ban, merge = _agnes_c(n, dys, code, alpha)
    height = ban[2:]
    return {
        "order": [int(v) for v in order],
        "height": [float(v) for v in height],
        "ac": bncoef(height),
        "merge": merge,
        "method": method_name,
        "data": None if data is None else data.tolist(),
    }


def diana(x, diss=False, metric="euclidean", stand=False, stop_at_k=False, keep_diss=None, keep_data=None):
    """Divisive analysis. Returns order, height, dc, and merge."""
    n, dys, data = _distances(x, diss, metric, stand)
    if n <= 1:
        raise ValueError("need at least 2 objects to cluster")
    order, ban, merge, _cs = _splyt(n, dys)
    height = ban[2:]
    return {
        "order": [int(v) for v in order],
        "height": [float(v) for v in height],
        "dc": bncoef(height),
        "merge": merge,
        "data": None if data is None else data.tolist(),
    }


def as_hclust(twins):
    """The fields ``plot.hclust`` reads from an agnes or diana object."""
    height = sorted(float(v) for v in twins["height"])
    labels = None
    return {
        "merge": twins["merge"],
        "height": height,
        "order": list(twins["order"]),
        "method": twins.get("method"),
    }
