"""Hartigan–Wong k-means (R ``stats`` ``kmns.f``, AS 136)."""

from __future__ import annotations

import math

BIG = 1.0e30


def _kmns(
    a: list[list[float]],
    c: list[list[float]],
    iter_max: int,
    qtran_max: int,
) -> tuple[list[list[float]], list[int], list[int], int, int]:
    """Run KMNS. ``a`` is m×n data, ``c`` is k×n initial centers (mutated)."""
    m = len(a)
    n = len(a[0]) if m else 0
    k = len(c)
    ic1 = [0] * m
    ic2 = [0] * m
    nc = [0] * k
    an1 = [0.0] * k
    an2 = [0.0] * k
    ncp = [0] * k
    d = [0.0] * m
    itran = [0] * k
    live = [0] * k

    ifault = 3
    if k <= 1 or k >= m:
        return c, ic1, [0.0] * k, 0, ifault
    ifault = 0

    for i in range(m):
        ic1[i] = 0
        ic2[i] = 1
        dt = [0.0, 0.0]
        for il in range(2):
            for j in range(n):
                da = a[i][j] - c[il][j]
                dt[il] += da * da
        if dt[0] > dt[1]:
            ic1[i], ic2[i] = 1, 0
            dt[0], dt[1] = dt[1], dt[0]
        for l in range(2, k):
            db = 0.0
            for j in range(n):
                dc = a[i][j] - c[l][j]
                db += dc * dc
                if db >= dt[1]:
                    break
            else:
                if db >= dt[0]:
                    dt[1] = db
                    ic2[i] = l
                else:
                    dt[1] = dt[0]
                    ic2[i] = ic1[i]
                    dt[0] = db
                    ic1[i] = l

    for l in range(k):
        nc[l] = 0
        for j in range(n):
            c[l][j] = 0.0
    for i in range(m):
        l = ic1[i]
        nc[l] += 1
        for j in range(n):
            c[l][j] += a[i][j]

    for l in range(k):
        if nc[l] == 0:
            return c, ic1, [0.0] * k, 0, 1
        aa = float(nc[l])
        for j in range(n):
            c[l][j] /= aa
        an2[l] = aa / (aa + 1.0)
        an1[l] = BIG
        if aa > 1.0:
            an1[l] = aa / (aa - 1.0)
        itran[l] = 1
        ncp[l] = -1

    indx = 0
    ij = 0
    for ij in range(1, iter_max + 1):
        indx = _optra(a, m, n, c, k, ic1, ic2, nc, an1, an2, ncp, d, itran, live, indx)
        if indx == m:
            break
        q_ok, indx = _qtran(
            a, m, n, c, k, ic1, ic2, nc, an1, an2, ncp, d, itran, indx, qtran_max
        )
        if not q_ok:
            ifault = 4
            break
        if k == 2:
            break
        for l in range(k):
            ncp[l] = 0
    else:
        ifault = 2

    wss = [0.0] * k
    for l in range(k):
        for j in range(n):
            c[l][j] = 0.0
    for i in range(m):
        ii = ic1[i]
        for j in range(n):
            c[ii][j] += a[i][j]
    for j in range(n):
        for l in range(k):
            c[l][j] /= float(nc[l])
        for i in range(m):
            ii = ic1[i]
            da = a[i][j] - c[ii][j]
            wss[ii] += da * da

    return c, ic1, wss, ij, ifault


def _optra(a, m, n, c, k, ic1, ic2, nc, an1, an2, ncp, d, itran, live, indx):
    for l in range(k):
        if itran[l] == 1:
            live[l] = m  # Fortran LIVE = M + 1 in 1-based indexing
    for i in range(m):
        indx += 1
        l1 = ic1[i]
        l2 = ic2[i]
        ll = l2
        if nc[l1] == 1:
            if indx == m:  # Fortran GO TO 90 still checks INDX == M
                for l in range(k):
                    itran[l] = 0
                    live[l] -= m
                return indx
            continue
        if ncp[l1] != 0:
            de = 0.0
            for j in range(n):
                df = a[i][j] - c[l1][j]
                de += df * df
            d[i] = de * an1[l1]
        da = 0.0
        for j in range(n):
            db = a[i][j] - c[l2][j]
            da += db * db
        r2 = da * an2[l2]
        new_l2 = l2
        for l in range(k):
            if (i >= live[l1] and i >= live[l]) or l == l1 or l == ll:
                continue
            rr = r2 / an2[l]
            dc = 0.0
            for j in range(n):
                dd = a[i][j] - c[l][j]
                dc += dd * dd
                if dc >= rr:
                    break
            else:
                r2 = dc * an2[l]
                new_l2 = l
        l2 = new_l2
        if r2 >= d[i]:
            ic2[i] = l2
        else:
            indx = 0
            live[l1] = m + i
            live[l2] = m + i
            ncp[l1] = i + 1  # 1-based step, as in Fortran
            ncp[l2] = i + 1
            al1 = float(nc[l1])
            alw = al1 - 1.0
            al2 = float(nc[l2])
            alt = al2 + 1.0
            for j in range(n):
                c[l1][j] = (c[l1][j] * al1 - a[i][j]) / alw
                c[l2][j] = (c[l2][j] * al2 + a[i][j]) / alt
            nc[l1] -= 1
            nc[l2] += 1
            an2[l1] = alw / al1
            an1[l1] = BIG
            if alw > 1.0:
                an1[l1] = alw / (alw - 1.0)
            an1[l2] = alt / al2
            an2[l2] = alt / (alt + 1.0)
            ic1[i] = l2
            ic2[i] = l1
        if indx == m:
            for l in range(k):
                itran[l] = 0
                live[l] -= m
            return indx
    for l in range(k):
        itran[l] = 0
        live[l] -= m
    return indx


def _qtran(a, m, n, c, k, ic1, ic2, nc, an1, an2, ncp, d, itran, indx, i_max_qtr):
    icoun = 0
    istep = 0
    while True:
        for i in range(m):
            icoun += 1
            istep += 1
            if istep >= i_max_qtr:
                return False, indx
            l1 = ic1[i]
            l2 = ic2[i]
            if nc[l1] == 1:
                if icoun == m:
                    return True, indx
                continue
            if istep <= ncp[l1]:
                da = 0.0
                for j in range(n):
                    db = a[i][j] - c[l1][j]
                    da += db * db
                d[i] = da * an1[l1]
            if istep < ncp[l1] or istep < ncp[l2]:
                r2 = d[i] / an2[l2]
                dd = 0.0
                for j in range(n):
                    de = a[i][j] - c[l2][j]
                    dd += de * de
                    if dd >= r2:
                        break
                else:
                    icoun = 0
                    indx = 0
                    itran[l1] = 1
                    itran[l2] = 1
                    ncp[l1] = istep + m
                    ncp[l2] = istep + m
                    al1 = float(nc[l1])
                    alw = al1 - 1.0
                    al2 = float(nc[l2])
                    alt = al2 + 1.0
                    for j in range(n):
                        c[l1][j] = (c[l1][j] * al1 - a[i][j]) / alw
                        c[l2][j] = (c[l2][j] * al2 + a[i][j]) / alt
                    nc[l1] -= 1
                    nc[l2] += 1
                    an2[l1] = alw / al1
                    an1[l1] = BIG
                    if alw > 1.0:
                        an1[l1] = alw / (alw - 1.0)
                    an1[l2] = alt / al2
                    an2[l2] = alt / (alt + 1.0)
                    ic1[i] = l2
                    ic2[i] = l1
            if icoun == m:
                return True, indx


def kmeans_hartigan_wong(
    x: list[list[float]],
    centers: int | list[list[float]],
    iter_max: int = 10,
    nstart: int = 1,
) -> dict:
    """R ``kmeans`` with algorithm Hartigan-Wong (default)."""
    m = len(x)
    if m == 0:
        raise ValueError("invalid nrow(x)")
    p = len(x[0])
    from boot import rng

    cn = None
    if isinstance(centers, int):
        k = centers
        picks = rng.sample_int(m, k, replace=False)
        center_matrix = [list(x[pick - 1]) for pick in picks]
        if nstart >= 2 or _duplicated(center_matrix):
            cn = _unique_rows(x)
            mm = len(cn)
            if mm < k:
                raise ValueError("more cluster centers than distinct data points.")
            picks = rng.sample_int(mm, k, replace=False)
            center_matrix = [list(cn[pick - 1]) for pick in picks]
    else:
        center_matrix = [list(row) for row in centers]
        if _duplicated(center_matrix):
            raise ValueError("initial centers are not distinct")
        k = len(center_matrix)
        if m < k:
            raise ValueError("more cluster centers than data points")
    if k == 1:
        return _kmeans_macqueen(x, center_matrix, iter_max)
    qtran_max = min(2**31 - 1, 50 * m)  # R: isteps.Qtran <- min(.Mimax, 50 * m)
    best_wss = math.inf
    best = None
    trials = [center_matrix]
    if nstart >= 2 and cn is not None:
        for _ in range(nstart - 1):
            picks = rng.sample_int(len(cn), k, replace=False)
            trials.append([list(cn[pick - 1]) for pick in picks])
    for trial_centers in trials:
        c = [list(row) for row in trial_centers]  # copy
        _, ic1, wss, iters, ifault = _kmns(x, c, iter_max, qtran_max)
        total = sum(wss)
        if total < best_wss:
            best_wss = total
            best = (c, ic1, wss, iters, ifault)
    assert best is not None
    c, ic1, wss, iters, ifault = best
    cluster = [code + 1 for code in ic1]
    return {
        "centers": c,
        "cluster": cluster,
        "withinss": wss,
        "tot.withinss": best_wss,
        "size": _cluster_sizes(cluster, k),
        "iter": iters,
        "ifault": ifault,
    }


def _kmeans_macqueen(x, center_matrix, iter_max):
    """MacQueen when k == 1 (R switches algorithm)."""
    k = len(center_matrix)
    m = len(x)
    p = len(x[0])
    c = [list(row) for row in center_matrix]
    cl = [0] * m
    for i in range(m):
        best = math.inf
        inew = 0
        for j in range(k):
            dd = sum((x[i][col] - c[j][col]) ** 2 for col in range(p))
            if dd < best:
                best = dd
                inew = j
        cl[i] = inew
    for j in range(k):
        for col in range(p):
            c[j][col] = 0.0
    nc = [0] * k
    for i in range(m):
        it = cl[i]
        nc[it] += 1
        for col in range(p):
            c[it][col] += x[i][col]
    for j in range(k):
        for col in range(p):
            c[j][col] /= nc[j]
    for _ in range(iter_max):
        updated = False
        for i in range(m):
            best = math.inf
            inew = 0
            for j in range(k):
                dd = sum((x[i][col] - c[j][col]) ** 2 for col in range(p))
                if dd < best:
                    best = dd
                    inew = j
            iold = cl[i]
            if iold != inew:
                updated = True
                cl[i] = inew
                nc[iold] -= 1
                nc[inew] += 1
                for col in range(p):
                    c[iold][col] += (c[iold][col] - x[i][col]) / nc[iold]
                    c[inew][col] += (x[i][col] - c[inew][col]) / nc[inew]
        if not updated:
            break
    wss = [0.0] * k
    for i in range(m):
        it = cl[i]
        for col in range(p):
            tmp = x[i][col] - c[it][col]
            wss[it] += tmp * tmp
    cluster = [code + 1 for code in cl]
    return {
        "centers": c,
        "cluster": cluster,
        "withinss": wss,
        "tot.withinss": sum(wss),
        "size": nc,
        "iter": iter_max,
        "ifault": 0,
    }


def _unique_rows(matrix):
    seen = []
    for row in matrix:
        key = tuple(row)
        if key not in seen:
            seen.append(key)
    return seen


def _duplicated(matrix):
    seen = set()
    for row in matrix:
        key = tuple(row)
        if key in seen:
            return True
        seen.add(key)
    return False


def _cluster_sizes(cluster, k):
    counts = [0] * k
    for code in cluster:
        counts[code - 1] += 1
    return counts
