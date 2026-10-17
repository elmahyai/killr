"""Fuzzy clustering, from ``src/fanny.c``."""

from __future__ import annotations

import math

import numpy as np

from cluster._dist import as_matrix, dysta3, fanny_index, missing_code, stand_matrix

_METRICS = ("euclidean", "manhattan", "SqEuclidean")


def _pow(base, exp):
    if base < 0.0 and not float(exp).is_integer():
        return float("nan")
    return math.pow(base, exp)


def _fuzzy(n, k, p, dss, memb_exp, tol, maxit, compute_p):
    dp = [[0.0] * k for _ in range(n)]
    esp = [0.0] * k
    ef = [0.0] * k
    if compute_p:
        p0 = 0.1 / (k - 1)
        for m in range(n):
            for j in range(k):
                p[m][j] = p0
        ndk = n // k
        nd = ndk
        j = 0
        for m in range(n):
            p[m][j] = 0.9
            if m + 1 >= nd:
                j += 1
                if j + 1 == k:
                    nd = n
                else:
                    nd += ndk
            for jj in range(k):
                p[m][jj] = _pow(p[m][jj], memb_exp)
    else:
        for m in range(n):
            for j in range(k):
                p[m][j] = _pow(p[m][j], memb_exp)

    cryt = 0.0
    for j in range(k):
        esp[j] = 0.0
        ef[j] = 0.0
        for m in range(n):
            esp[j] += p[m][j]
            for i in range(n):
                if i == m:
                    continue
                mi = fanny_index(m, i, n)
                dp[m][j] += p[i][j] * dss[mi]
                ef[j] += p[i][j] * p[m][j] * dss[mi]
        cryt += ef[j] / (esp[j] * 2.0)
    crt = cryt
    reen = 1.0 / (memb_exp - 1.0)
    it = 0
    converged = False
    while True:
        it += 1
        if it > maxit:
            break
        for m in range(n):
            pt = [0.0] * k
            dt = 0.0
            for j in range(k):
                pt[j] = _pow(esp[j] / (dp[m][j] - ef[j] / (2.0 * esp[j])), reen)
                dt += pt[j]
            xx = 0.0
            for j in range(k):
                pt[j] /= dt
                if pt[j] < 0.0:
                    xx += pt[j]
            for j in range(k):
                pt[j] = _pow(pt[j] / (1.0 - xx), memb_exp) if pt[j] > 0.0 else 0.0
                d_mj = pt[j] - p[m][j]
                esp[j] += d_mj
                for i in range(n):
                    if i == m:
                        continue
                    mi = fanny_index(m, i, n)
                    ddd = d_mj * dss[mi]
                    dp[i][j] += ddd
                    ef[j] += p[i][j] * 2.0 * ddd
                p[m][j] = pt[j]
        cryt = 0.0
        for j in range(k):
            cryt += ef[j] / (esp[j] * 2.0)
        if abs(cryt - crt) <= tol * cryt:
            converged = True
            break
        crt = cryt
    iterations = it if converged else -1
    crt = sum(esp) / n
    xx = _pow(float(k), memb_exp - 1.0)
    normalized = (xx * crt - 1.0) / (xx - 1.0)
    inv = 1.0 / memb_exp
    for m in range(n):
        for j in range(k):
            p[m][j] = _pow(p[m][j], inv)
    return cryt, crt, normalized, iterations, converged


def _caddy(n, k, p):
    nfuzz = [0] * k
    ncluv = [0] * n
    pbest = p[0][0]
    nbest = 1
    for i in range(1, k):
        if pbest < p[0][i]:
            pbest = p[0][i]
            nbest = i + 1
    nfuzz[0] = nbest
    ncluv[0] = 1
    ktrue = 1
    for m in range(1, n):
        pbest = p[m][0]
        nbest = 1
        for i in range(1, k):
            if pbest < p[m][i]:
                pbest = p[m][i]
                nbest = i + 1
        stay = False
        for ktry in range(ktrue):
            if nfuzz[ktry] == nbest:
                stay = True
                ncluv[m] = ktry + 1
                break
        if not stay:
            nfuzz[ktrue] = nbest
            ktrue += 1
            ncluv[m] = ktrue
    if ktrue < k:
        for kwalk in range(ktrue, k):
            for kleft in range(1, k + 1):
                if all(nfuzz[ktry] != kleft for ktry in range(kwalk)):
                    nfuzz[kwalk] = kleft
                    break
    for m in range(n):
        drawn = [p[m][nfuzz[i] - 1] for i in range(k)]
        for i in range(k):
            p[m][i] = drawn[i]
    return ktrue, ncluv


def _fygur(ktrue, n, ncluv, dss, s):
    clustering = [0] + ncluv
    rows = []
    avsyl = [0.0] * (ktrue + 1)
    ttsyl = 0.0
    for k in range(1, ktrue + 1):
        nelem = [j for j in range(1, n + 1) if clustering[j] == k]
        ntt = len(nelem)
        syl = [0.0] * ntt
        negbr = [-1] * ntt
        for j, nj in enumerate(nelem):
            dysb = s * 1.1 + 1.0
            for k_ in range(1, ktrue + 1):
                if k_ == k:
                    continue
                db = 0.0
                nbb = 0
                for l in range(1, n + 1):
                    if clustering[l] != k_:
                        continue
                    nbb += 1
                    if l != nj:
                        db += dss[fanny_index(nj - 1, l - 1, n)]
                db /= nbb
                if dysb > db:
                    dysb = db
                    negbr[j] = k_
            if ntt > 1:
                dysa = 0.0
                for nl in nelem:
                    if nj != nl:
                        dysa += dss[fanny_index(nj - 1, nl - 1, n)]
                dysa /= ntt - 1
                if dysa > 0.0:
                    if dysb > 0.0:
                        if dysb > dysa:
                            syl[j] = 1.0 - dysa / dysb
                        elif dysb < dysa:
                            syl[j] = dysb / dysa - 1.0
                        else:
                            syl[j] = 0.0
                        syl[j] = min(1.0, max(-1.0, syl[j]))
                    else:
                        syl[j] = -1.0
                elif dysb > 0.0:
                    syl[j] = 1.0
                else:
                    syl[j] = 0.0
            else:
                syl[j] = 0.0
        pending = syl[:]
        order = []
        av = 0.0
        for _j in range(ntt):
            lang = max(range(ntt), key=lambda l: pending[l])
            # ties: the C scan keeps the first maximum only when strictly greater,
            # so an equal later value does not replace. max() keeps the first max. Good.
            symax = pending[lang]
            # fix: Python max returns the first maximum. C uses `if (symax < syl[l])`,
            # so equals keep the earlier index. Python max is the same. 
            order.append(lang)
            av += symax
            pending[lang] = -3.0
        ttsyl += av
        avsyl[k] = av / ntt
        if ntt < 2:
            rows.append([float(k), float(negbr[0]), 0.0, float(nelem[0])])
        else:
            for lang in order:
                rows.append([float(k), float(negbr[lang]), syl[lang], float(nelem[lang])])
    return rows, avsyl[1:], ttsyl / n


def fanny(x, k, diss=False, memb_exp=2, metric="euclidean", stand=False, ini_mem=None, cluster_only=False, maxit=500, tol=1e-15):
    """Fuzzy analysis. Membership rows sum to one after the crisp reordering of columns."""
    metric = str(metric)
    if metric not in _METRICS:
        # match.arg accepts a unique prefix
        hits = [name for name in _METRICS if name.startswith(metric)]
        if len(hits) != 1:
            raise ValueError("invalid metric")
        metric = hits[0]
    ndyst = _METRICS.index(metric) + 1
    if diss:
        raw = np.asarray(x, dtype=float).reshape(-1)
        n = int(round((1 + math.sqrt(1 + 8 * raw.size)) / 2))
        dss = raw.tolist() + [0.0]
        data = None
    else:
        data = as_matrix(x)
        if stand:
            data = stand_matrix(data)
        filled, jtmd, valmd, _missing = missing_code(data)
        jt = None if jtmd is None else [jtmd[j + 1] for j in range(data.shape[1])]
        vm = None if valmd is None else [valmd[j + 1] for j in range(data.shape[1])]
        dss, jhalt = dysta3(filled, ndyst, jt, vm)
        if jhalt:
            raise ValueError("No clustering performed, NA-values in the dissimilarity matrix.")
        n = data.shape[0]
    k = int(k)
    if k < 1 or k > n // 2 - 1:
        raise ValueError("'k' (number of clusters) must be in {1,2, .., n/2 -1}")
    memb_exp = float(memb_exp)
    if not math.isfinite(memb_exp) or memb_exp <= 1.0:
        raise ValueError("'memb.exp' must be a finite number > 1")
    maxit = int(maxit)
    if maxit < 0:
        raise ValueError("'maxit' must be non-negative integer")
    if ini_mem is None:
        p = [[0.0] * k for _ in range(n)]
        compute_p = True
    else:
        p = np.asarray(ini_mem, dtype=float).tolist()
        compute_p = False
    cryt, dunn, normalized, iterations, converged = _fuzzy(
        n, k, p, dss, memb_exp, float(tol), maxit, compute_p
    )
    ktrue, clustering = _caddy(n, k, p)
    if abs(memb_exp - 2.0) < 0.0 or memb_exp == 2:
        coeff = [dunn, normalized]
    else:
        cf = sum(value * value for row in p for value in row) / n
        coeff = [cf, (k * cf - 1.0) / (k - 1.0)]
    result = {
        "membership": p,
        "coeff": coeff,
        "memb_exp": memb_exp,
        "clustering": clustering,
        "k_crisp": int(ktrue),
        "objective": [float(cryt), float(tol)],
        "convergence": [int(iterations), bool(converged), int(maxit)],
    }
    if k != 1 and not cluster_only and 2 <= ktrue < n:
        s = max(dss[: n * (n - 1) // 2])
        rows, av, tts = _fygur(ktrue, n, clustering, dss, s)
        av = av + [0.0] * (k - len(av))
        result["silinfo"] = {
            "widths": [[row[0], row[1], row[2]] for row in rows],
            "index": [int(row[3]) for row in rows],
            "clus_avg_widths": av,
            "avg_width": tts,
        }
    return result
