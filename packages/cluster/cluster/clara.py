"""Clustering large applications, from ``src/clara.c``.

The default generator is clara's 16-bit ``randm``, not R's Mersenne-Twister.
"""

from __future__ import annotations

import math

import numpy as np

from cluster._dist import as_matrix, ind_2, stand_matrix

_EUCLIDEAN = 1
_MANHATTAN = 2
_JACCARD = 3


def _randm(nrun):
    nrun = (nrun * 5761 + 999) & 0xFFFF
    return nrun, nrun / 65536.0


def _draw(n, nrun, rng):
    if rng is None:
        nrun, u = _randm(nrun)
    else:
        u = rng()
        nrun = 0
    rand_k = 1 + int(n * u)
    if rand_k > n:
        rand_k = n
    return nrun, rand_k


def _dysta2(nsam, nsel, data, diss_kind):
    """Distances among the sample. ``nsel`` is 0-based list of 1-based row numbers."""
    n, p = data.shape
    n_dys = nsam * (nsam - 1) // 2
    dys = [0.0] * (n_dys + 1)
    nlk = 0
    for left in range(1, nsam):
        lsel = nsel[left]
        for right in range(left):
            ksel = nsel[right]
            nlk += 1
            clk = 0.0
            present = 0
            ones = 0
            for column in range(p):
                a = data[lsel - 1, column]
                b = data[ksel - 1, column]
                present += 1
                if diss_kind == _EUCLIDEAN:
                    diff = a - b
                    clk += diff * diff
                elif diss_kind == _JACCARD:
                    if a > 0.9 and b > 0.9:
                        clk += 1.0
                        ones += 1
                    elif a > 0.9 or b > 0.9:
                        ones += 1
                else:
                    clk += abs(a - b)
            if present == 0:
                dys[nlk] = -1.0
            elif diss_kind == _EUCLIDEAN:
                dys[nlk] = math.sqrt(clk * (p / present))
            elif diss_kind == _JACCARD:
                dys[nlk] = 1.0 - clk / ones
            else:
                dys[nlk] = clk * (p / present)
    return dys


def _bswap2(kk, nsam, dys, pam_like):
    s = 0.0
    for value in dys[1:]:
        if s < value:
            s = value
    s_large = s * 1.1 + 1.0
    nrepr = [0] * (nsam + 1)
    dysma = [s_large] * (nsam + 1)
    dysmb = [0.0] * (nsam + 1)
    for _k in range(kk):
        nmax = -1
        ammax = 0.0
        for i in range(1, nsam + 1):
            if nrepr[i] != 0:
                continue
            beter = 0.0
            for j in range(1, nsam + 1):
                cmd = dysma[j] - dys[ind_2(i, j)]
                if cmd > 0.0:
                    beter += cmd
            if ammax <= beter:
                ammax = beter
                nmax = i
        nrepr[nmax] = 1
        for j in range(1, nsam + 1):
            ij = ind_2(nmax, j)
            if dysma[j] > dys[ij]:
                dysma[j] = dys[ij]
    sky = sum(dysma[1:])
    if kk == 1:
        return nrepr
    while True:
        for j in range(1, nsam + 1):
            dysma[j] = s_large
            dysmb[j] = s_large
            for i in range(1, nsam + 1):
                if not nrepr[i]:
                    continue
                ij = ind_2(i, j)
                if dysma[j] > dys[ij]:
                    dysmb[j] = dysma[j]
                    dysma[j] = dys[ij]
                elif dysmb[j] > dys[ij]:
                    dysmb[j] = dys[ij]
        dzsky = 1.0
        hbest = nbest = -1
        for h in range(1, nsam + 1):
            if nrepr[h]:
                continue
            for i in range(1, nsam + 1):
                if not nrepr[i]:
                    continue
                dz = 0.0
                for j in range(1, nsam + 1):
                    ij = ind_2(i, j)
                    hj = ind_2(h, j)
                    if dys[ij] == dysma[j]:
                        if pam_like:
                            small = dys[hj] if dysmb[j] > dys[hj] else dysmb[j]
                        else:
                            small = dys[hj] if dysmb[j] > dys[ij] else dysmb[j]
                        dz += -dysma[j] + small
                    elif dys[hj] < dysma[j]:
                        dz += -dysma[j] + dys[hj]
                if dzsky > dz:
                    dzsky = dz
                    hbest = h
                    nbest = i
        if dzsky < 0.0:
            nrepr[hbest] = 1
            nrepr[nbest] = 0
            sky += dzsky
            continue
        break
    return nrepr


def _pair_distance(data, diss_kind, left, right, correct_d, has_na):
    """Return (distance_for_comparison, present). Squared Euclidean is not rooted yet."""
    n, p = data.shape
    if left == right:
        return 0.0, p
    dsum = 0.0
    tra = 0.0
    ones = 0
    present = 0
    for column in range(p):
        a = data[left - 1, column]
        b = data[right - 1, column]
        if has_na and (math.isnan(a) or math.isnan(b)):
            continue
        present += 1
        if diss_kind == _JACCARD:
            if a > 0.9 and b > 0.9:
                tra += 1.0
                ones += 1
            elif a > 0.9 or b > 0.9:
                ones += 1
        else:
            gap = abs(a - b)
            if diss_kind == _EUCLIDEAN:
                gap *= gap
            dsum += gap
    if diss_kind == _JACCARD:
        dsum = 1.0 - tra / ones if ones else float("nan")
    if has_na:
        if present == 0:
            return None, 0
        if correct_d:
            dsum *= p / present
        else:
            dsum *= present / p
    return dsum, present


def _selec(kk, n, data, diss_kind, nsam, nrepr, nsel, dys, correct_d, has_na):
    nr = [0] * (kk + 1)
    ns = [0] * (kk + 1)
    np_ = [0] * (kk + 1)
    ttd = [0.0] * (kk + 1)
    radus = [-1.0] * (kk + 1)
    ratt = [0.0] * (kk + 1)
    jk = 0
    for j in range(1, nsam + 1):
        if nrepr[j] != 0:
            jk += 1
            nr[jk] = nsel[j - 1]
            np_[jk] = j
    zb = 0.0
    new = [0] * (kk + 1)
    newf = 0
    for i in range(1, n + 1):
        jkabc = -1
        dnull = -9.0
        if not has_na:
            for cluster in range(1, kk + 1):
                dsum, _present = _pair_distance(data, diss_kind, nr[cluster], i, False, False)
                if cluster != 1 and dsum >= dnull:
                    continue
                dnull = dsum
                jkabc = cluster
        else:
            first = True
            found = False
            for cluster in range(1, kk + 1):
                dsum, present = _pair_distance(data, diss_kind, nr[cluster], i, correct_d, True)
                if nr[cluster] != i and present == 0:
                    continue
                if first:
                    first = False
                    found = True
                elif dnull <= dsum:
                    continue
                dnull = dsum
                jkabc = cluster
                found = True
            if not found:
                return True, None
        if diss_kind == _EUCLIDEAN:
            dnull = math.sqrt(dnull)
        zb += dnull
        ttd[jkabc] += dnull
        if radus[jkabc] < dnull:
            radus[jkabc] = dnull
        ns[jkabc] += 1
        if newf < kk:
            if newf != 0 and any(new[jnew] == jkabc for jnew in range(1, newf + 1)):
                pass
            else:
                newf += 1
                new[newf] = jkabc
    nr_new = [0] * (kk + 1)
    ns_new = [0] * (kk + 1)
    np_new = [0] * (kk + 1)
    tt_new = [0.0] * (kk + 1)
    rd_new = [0.0] * (kk + 1)
    for j in range(1, kk + 1):
        nj = new[j]
        nr_new[j] = nr[nj]
        ns_new[j] = ns[nj]
        np_new[j] = np_[nj]
        tt_new[j] = ttd[nj]
        rd_new[j] = radus[nj]
    for j in range(1, kk + 1):
        nr[j] = nr_new[j]
        ns[j] = ns_new[j]
        np_[j] = np_new[j]
        ttd[j] = tt_new[j] / ns[j]
        radus[j] = rd_new[j]
    if kk > 1:
        for ka in range(1, kk + 1):
            first = True
            npa = np_[ka]
            for kb in range(1, kk + 1):
                if kb == ka:
                    continue
                npab = ind_2(npa, np_[kb])
                if first:
                    first = False
                elif dys[npab] >= ratt[ka]:
                    continue
                ratt[ka] = dys[npab]
                if ratt[ka] == 0.0:
                    ratt[ka] = -1.0
            if ratt[ka] > -0.5:
                ratt[ka] = radus[ka] / ratt[ka]
    return False, {
        "nr": nr[1:],
        "ttd": ttd[1:],
        "radus": radus[1:],
        "ratt": ratt[1:],
        "zb": zb,
    }


def _resul(kk, n, data, diss_kind, nrx, correct_d, has_na):
    clustering = [0] * n
    for i in range(n):
        if any(nrx[jk] == i + 1 for jk in range(kk)):
            continue
        dnull = None
        jksky = 0
        for jk in range(kk):
            dsum, present = _pair_distance(data, diss_kind, nrx[jk], i + 1, correct_d, has_na)
            if diss_kind == _EUCLIDEAN and dsum is not None:
                dsum = math.sqrt(dsum)
            if jk == 0 or dnull > dsum:
                dnull = dsum
                jksky = jk
        clustering[i] = jksky + 1
    for jk in range(kk):
        clustering[nrx[jk] - 1] = jk + 1
    sizes = [0] * kk
    for label in clustering:
        sizes[label - 1] += 1
    return clustering, sizes


def _black(kk, nsam, nbest, dys, s, clustering):
    ncluv = [int(clustering[nbest[l] - 1]) for l in range(nsam)]
    rows = []
    avsyl = [0.0] * kk
    ttsyl = 0.0
    labels = [0] + ncluv
    for numcl in range(1, kk + 1):
        nelem = [j for j in range(1, nsam + 1) if labels[j] == numcl]
        ntt = len(nelem)
        syl = [0.0] * (ntt + 1)
        negbr = [-1] * (ntt + 1)
        for j in range(1, ntt + 1):
            nj = nelem[j - 1]
            dysb = s * 1.1 + 1.0
            for nclu in range(1, kk + 1):
                if nclu == numcl:
                    continue
                members = [l for l in range(1, nsam + 1) if labels[l] == nclu]
                db = sum(dys[ind_2(nj, l)] for l in members) / len(members)
                if db < dysb:
                    dysb = db
                    negbr[j] = nclu
            if ntt == 1:
                syl[j] = 0.0
                continue
            dysa = sum(dys[ind_2(nj, nelem[l - 1])] for l in range(1, ntt + 1)) / (ntt - 1)
            if dysa <= 0.0:
                syl[j] = 1.0 if dysb > 0.0 else 0.0
                continue
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
        av = 0.0
        pending = syl[:]
        order = []
        for _j in range(1, ntt + 1):
            lang = 1
            symax = -2.0
            for l in range(1, ntt + 1):
                if pending[l] > symax:
                    symax = pending[l]
                    lang = l
            order.append(lang)
            av += symax
            pending[lang] = -3.0
        ttsyl += av
        avsyl[numcl - 1] = av / ntt
        if ntt >= 2:
            for place, lang in enumerate(order, start=1):
                rows.append(
                    [
                        float(numcl),
                        float(negbr[lang]),
                        pending and syl[lang],
                        float(nbest[nelem[lang - 1] - 1]),
                    ]
                )
        else:
            rows.append([float(numcl), float(negbr[1]), 0.0, float(nbest[nelem[0] - 1])])
    return rows, avsyl, ttsyl / nsam


def clara(
    x,
    k,
    metric="euclidean",
    stand=False,
    cluster_only=False,
    samples=5,
    sampsize=None,
    medoids_x=True,
    keep_data=None,
    rng_r=False,
    pam_like=False,
    correct_d=True,
    rng=None,
):
    """CLARA. ``rng`` supplies uniforms in place of ``randm`` when ``rng_r`` is true."""
    names = {"euclidean": _EUCLIDEAN, "manhattan": _MANHATTAN, "jaccard": _JACCARD}
    if metric not in names and not any(name.startswith(str(metric)) for name in names):
        raise ValueError("invalid metric")
    if metric not in names:
        metric = next(name for name in names if name.startswith(str(metric)))
    diss_kind = names[metric]
    original = as_matrix(x)
    n, p = original.shape
    k = int(k)
    if k < 1 or k > n - 1:
        raise ValueError("The number of clusters should be at least 1 and at most n-1.")
    if sampsize is None:
        sampsize = min(n, 40 + 2 * k)
    sampsize = int(sampsize)
    samples = int(samples)
    if sampsize < max(2, k + 1):
        raise ValueError("'sampsize' should be at least max(2, 1+ number of clusters)")
    if n < sampsize:
        raise ValueError("'sampsize' should not be larger than the number of objects")
    if samples < 1:
        raise ValueError("'samples' should be at least 1")
    data = stand_matrix(original) if stand else original.copy()
    has_na = bool(np.isnan(data).any())
    if has_na and not correct_d:
        correct_d = False
    full_sample = n == sampsize
    lrg_sam = n < 2 * sampsize
    n_sam = (n - sampsize) if lrg_sam else sampsize
    nrun = 0
    kall = False
    nunfs = 0
    zba = -1.0
    sx = -1.0
    nrx = [0] * k
    nbest = [0] * sampsize
    ttbes = [0.0] * k
    rdbes = [0.0] * k
    rabes = [0.0] * k
    use_rng = rng if rng_r else None
    for jran in range(1, samples + 1):
        nsel = [0] * sampsize
        if not full_sample:
            ntt = 0
            if kall and nunfs + 1 != jran and not lrg_sam:
                nsel[:k] = nrx[:k]
                for jk in range(k - 1):
                    nsm = nsel[jk]
                    jsm = jk
                    for jkk in range(jk + 1, k):
                        if nsm > nsel[jkk]:
                            nsm = nsel[jkk]
                            jsm = jkk
                    nsel[jsm] = nsel[jk]
                    nsel[jk] = nsm
                ntt = k
            else:
                while True:
                    nrun, rand_k = _draw(n, nrun, use_rng)
                    if kall and any(rand_k == nrx[jk] for jk in range(k)):
                        continue
                    break
                nsel[ntt] = rand_k
                ntt += 1
            while ntt < n_sam:
                while True:
                    nrun, rand_k = _draw(n, nrun, use_rng)
                    if kall and lrg_sam and any(rand_k == nrx[jk] for jk in range(k)):
                        continue
                    placed = False
                    for ka in range(ntt):
                        if nsel[ka] >= rand_k:
                            if nsel[ka] == rand_k:
                                placed = False
                                break
                            for na in range(ntt, ka, -1):
                                nsel[na] = nsel[na - 1]
                            nsel[ka] = rand_k
                            placed = True
                            break
                    else:
                        nsel[ntt] = rand_k
                        placed = True
                    if placed:
                        break
                ntt += 1
            if lrg_sam:
                chosen = set(nsel[:n_sam])
                sample = [j for j in range(1, n + 1) if j not in chosen]
                nsel = sample
        else:
            nsel = list(range(1, nsam + 1)) if False else list(range(1, sampsize + 1))
        dys = _dysta2(sampsize, nsel, data, diss_kind)
        nrepr = _bswap2(k, sampsize, dys, bool(pam_like))
        failed, info = _selec(k, n, data, diss_kind, sampsize, nrepr, nsel, dys, bool(correct_d), has_na)
        if failed:
            nunfs += 1
        elif (not kall) or zba > info["zb"]:
            kall = True
            zba = info["zb"]
            ttbes = info["ttd"]
            rdbes = info["radus"]
            rabes = info["ratt"]
            nrx = info["nr"]
            nbest = nsel[:sampsize]
            sx = max(dys[1:])
        if full_sample:
            break
    if nunfs >= samples or not kall:
        raise ValueError("clara failed to build a usable sample")
    dys = _dysta2(sampsize, nbest, data, diss_kind)
    clustering, sizes = _resul(k, n, data, diss_kind, nrx, bool(correct_d), has_na)
    if cluster_only:
        return clustering
    result = {
        "sample": [int(v) for v in nbest],
        "medoids": original[np.array(nrx) - 1].tolist() if medoids_x else None,
        "i_med": [int(v) for v in nrx],
        "clustering": [int(v) for v in clustering],
        "objective": float(zba / n),
        "clusinfo": [
            [float(sizes[j]), float(rdbes[j]), float(ttbes[j]), float(rabes[j])] for j in range(k)
        ],
        "data": data.tolist() if keep_data or (keep_data is None and medoids_x) else None,
    }
    if k > 1:
        rows, avsil, ttsil = _black(k, sampsize, nbest, dys, sx, clustering)
        result["silinfo"] = {
            "widths": [[row[0], row[1], row[2]] for row in rows],
            "index": [int(row[3]) for row in rows],
            "clus_avg_widths": [float(v) for v in avsil],
            "avg_width": float(ttsil),
        }
    return result
