"""Random forest training and prediction.

Classification trees are grown by the Rust port of ``rfsub.f``. Regression
trees and the C driver (sampling, out-of-bag votes, importance) are Python.
Draws come from ``boot.rng``, which matches R's ``unif_rand``.
"""

from __future__ import annotations

import ctypes
import math
import sys
from pathlib import Path

import numpy as np

from randomForest.qsort import r_qsort_i

_PACKAGES = Path(__file__).resolve().parents[2]
if str(_PACKAGES / "boot") not in sys.path:
    sys.path.insert(0, str(_PACKAGES / "boot"))
from boot.rng import sample_int, unif  # noqa: E402

_MAX_CAT = 53
_NODE_TERMINAL = -1
_NODE_TOSPLIT = -2
_NODE_INTERIOR = -3

_LIB = None
_UNIF = None


def _library():
    global _LIB, _UNIF
    if _LIB is not None:
        return _LIB
    path = _PACKAGES.parent / "crates" / "rfsub" / "target" / "release" / "librfsub.so"
    if not path.is_file():
        raise FileNotFoundError(f"build crates/rfsub first; missing {path}")
    lib = ctypes.CDLL(str(path))

    def _draw():
        return unif()

    _UNIF = ctypes.CFUNCTYPE(ctypes.c_double)(_draw)
    lib.rfsub_set_unif(_UNIF)
    lib.rfsub_buildtree.argtypes = [
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
    ]
    _LIB = lib
    return lib


def _as_matrix(values):
    data = np.asarray(values, dtype=float)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    if data.ndim != 2:
        raise ValueError("predictors must be a matrix")
    return np.ascontiguousarray(data)


def _factor(labels):
    text = [str(item) for item in labels]
    levels = sorted(set(text))
    codes = [levels.index(item) + 1 for item in text]
    return codes, levels


def _r_round(value):
    return int(round(float(value)))


def _sample_rows(population, size, replace):
    if replace:
        return [int(unif() * population) for _ in range(size)]
    indices = list(range(population))
    last = population - 1
    chosen = []
    for _ in range(size):
        current = int(unif() * (last + 1))
        chosen.append(indices[current])
        indices[current], indices[last] = indices[last], indices[current]
        last -= 1
    return chosen


def _permute_oob(column, flat, inbag, nsample, mdim):
    held = [flat[column + i * mdim] for i in range(nsample) if inbag[i] == 0]
    last = len(held)
    for _ in range(len(held)):
        k = int(last * unif())
        held[last - 1], held[k] = held[k], held[last - 1]
        last -= 1
    cursor = 0
    for i in range(nsample):
        if inbag[i] == 0:
            flat[column + i * mdim] = held[cursor]
            cursor += 1


def _make_a(flat, mdim, nsample, cat):
    order = [0] * (mdim * nsample)
    ranks = [0] * (mdim * nsample)
    for variable in range(mdim):
        if cat[variable] == 1:
            values = [flat[variable + j * mdim] for j in range(nsample)]
            index = [j + 1 for j in range(nsample)]
            r_qsort_i(values, index, 1, nsample)
            for j in range(nsample - 1):
                n1 = index[j]
                n2 = index[j + 1]
                order[variable + j * mdim] = n1
                if j == 0:
                    ranks[variable + (n1 - 1) * mdim] = 1
                previous = ranks[variable + (n1 - 1) * mdim]
                ranks[variable + (n2 - 1) * mdim] = previous + 1 if values[j] < values[j + 1] else previous
            order[variable + (nsample - 1) * mdim] = index[nsample - 1]
        else:
            for j in range(nsample):
                order[variable + j * mdim] = int(flat[variable + j * mdim])
    return order, ranks


def _mod_a(order, nsample, mdim, cat, maxcat, inbag):
    nuse = sum(1 for flag in inbag if flag)
    for variable in range(mdim):
        if cat[variable] != 1:
            continue
        k = 0
        nt = 0
        while nt < nuse:
            if inbag[order[variable + k * mdim] - 1]:
                order[variable + nt * mdim] = order[variable + k * mdim]
                k += 1
            else:
                for m in range(nsample - k):
                    if inbag[order[variable + (k + m) * mdim] - 1]:
                        order[variable + nt * mdim] = order[variable + (k + m) * mdim]
                        k += m + 1
                        break
            nt += 1
    ncase = [0] * nsample
    if maxcat > 1:
        k = 0
        nt = 0
        while nt < nuse:
            if inbag[k]:
                k += 1
                ncase[nt] = k
            else:
                for j in range(nsample - k):
                    if inbag[k + j]:
                        ncase[nt] = k + j + 1
                        k += j + 1
                        break
            nt += 1
            if nt >= nuse:
                break
    return nuse, ncase


def _xtranslate(flat, mdim, bestvar, bestsplit, bestsplitnext, nodestatus, cat, tree_size, xbestsplit):
    for i in range(tree_size):
        if nodestatus[i] == 1:
            m = bestvar[i] - 1
            if cat[m] == 1:
                left = int(bestsplit[i]) - 1
                right = int(bestsplitnext[i]) - 1
                xbestsplit[i] = 0.5 * (flat[m + left * mdim] + flat[m + right * mdim])
            else:
                xbestsplit[i] = bestsplit[i]


def _predict_class_tree(flat, n, mdim, treemap, nodestatus, xbestsplit, bestvar, nodeclass, tree_size, cat, maxcat):
    decoded = None
    if maxcat > 1:
        decoded = [0] * (maxcat * tree_size)
        for i in range(tree_size):
            if nodestatus[i] != _NODE_TERMINAL and cat[bestvar[i] - 1] > 1:
                packed = xbestsplit[i]
                for j in range(cat[bestvar[i] - 1]):
                    decoded[j + i * maxcat] = 1 if (int(packed) & 1) else 0
                    packed = packed / 2.0
    labels = [0] * n
    nodes = [0] * n
    for i in range(n):
        k = 0
        while nodestatus[k] != _NODE_TERMINAL:
            m = bestvar[k] - 1
            if cat[m] == 1:
                k = treemap[k * 2] - 1 if flat[m + i * mdim] <= xbestsplit[k] else treemap[1 + k * 2] - 1
            else:
                bit = decoded[int(flat[m + i * mdim]) - 1 + k * maxcat]
                k = treemap[k * 2] - 1 if bit else treemap[1 + k * 2] - 1
        labels[i] = nodeclass[k]
        nodes[i] = k + 1
    return labels, nodes


def _tie_update(qq, smaxtr, jest, ntie, j):
    if qq > smaxtr:
        smaxtr = qq
        jest = j + 1
        ntie = 1
    if qq == smaxtr:
        ntie += 1
        if unif() < 1.0 / ntie:
            smaxtr = qq
            jest = j + 1
    return smaxtr, jest, ntie


def _oob(nsample, nclass, cl, jtr, counttr, out, cutoff):
    jest = [0] * nsample
    errtr = [0.0] * (nclass + 1)
    noob = 0
    noobcl = [0] * nclass
    for n in range(nsample):
        if out[n]:
            noob += 1
            noobcl[cl[n] - 1] += 1
            smaxtr = 0.0
            ntie = 1
            prediction = 0
            for j in range(nclass):
                qq = (counttr[j + n * nclass] / out[n]) / cutoff[j]
                smaxtr, prediction, ntie = _tie_update(qq, smaxtr, prediction, ntie, j)
            jest[n] = prediction
            if prediction != cl[n]:
                errtr[cl[n]] += 1.0
                errtr[0] += 1.0
    errtr[0] = errtr[0] / noob if noob else math.inf
    for n in range(1, nclass + 1):
        denom = noobcl[n - 1]
        errtr[n] = errtr[n] / denom if denom else (math.inf if errtr[n] else math.nan)
    return jest, errtr


def _norm_class_wt(nsample, nclass, use_wt, classwt, class_freq):
    weights = list(classwt)
    if use_wt:
        total = sum(weights)
        weights = [item / total for item in weights]
    else:
        weights = [class_freq[i] / nsample for i in range(nclass)]
    return [weights[i] * nsample / class_freq[i] if class_freq[i] else 0.0 for i in range(nclass)]


def _buildtree(order, ranks, cl, cat, maxcat, mdim, nsample, nclass, nrnodes, ndsize, ncase, mtry, nuse, win, tclasspop, tgini):
    lib = _library()
    a = np.array(order, dtype=np.int32)
    b = np.array(ranks, dtype=np.int32)
    cl_a = np.array(cl, dtype=np.int32)
    cat_a = np.array(cat, dtype=np.int32)
    treemap = np.zeros(2 * nrnodes, dtype=np.int32)
    bestvar = np.zeros(nrnodes, dtype=np.int32)
    bestsplit = np.zeros(nrnodes, dtype=np.float64)
    bestsplitnext = np.zeros(nrnodes, dtype=np.float64)
    tgini_a = np.array(tgini, dtype=np.float64)
    nodestatus = np.zeros(nrnodes, dtype=np.int32)
    nodepop = np.zeros(nrnodes, dtype=np.int32)
    nodestart = np.zeros(nrnodes, dtype=np.int32)
    classpop = np.zeros(nclass * nrnodes, dtype=np.float64)
    tclasspop_a = np.array(tclasspop, dtype=np.float64)
    tclasscat = np.zeros(nclass * 53, dtype=np.float64)
    ta = np.zeros(nsample, dtype=np.int32)
    idmove = np.zeros(nsample, dtype=np.int32)
    ncase_a = np.array(ncase, dtype=np.int32)
    iv = np.zeros(mdim, dtype=np.int32)
    nodeclass = np.zeros(nrnodes, dtype=np.int32)
    ndbigtree = ctypes.c_int(0)
    win_a = np.array(win, dtype=np.float64)
    wr = np.zeros(nclass, dtype=np.float64)
    wl = np.zeros(nclass, dtype=np.float64)
    mind = np.zeros(mdim, dtype=np.int32)
    i32 = ctypes.POINTER(ctypes.c_int)
    f64 = ctypes.POINTER(ctypes.c_double)
    lib.rfsub_buildtree(
        a.ctypes.data_as(i32),
        b.ctypes.data_as(i32),
        cl_a.ctypes.data_as(i32),
        cat_a.ctypes.data_as(i32),
        int(maxcat),
        int(mdim),
        int(nsample),
        int(nclass),
        treemap.ctypes.data_as(i32),
        bestvar.ctypes.data_as(i32),
        bestsplit.ctypes.data_as(f64),
        bestsplitnext.ctypes.data_as(f64),
        tgini_a.ctypes.data_as(f64),
        nodestatus.ctypes.data_as(i32),
        nodepop.ctypes.data_as(i32),
        nodestart.ctypes.data_as(i32),
        classpop.ctypes.data_as(f64),
        tclasspop_a.ctypes.data_as(f64),
        tclasscat.ctypes.data_as(f64),
        ta.ctypes.data_as(i32),
        int(nrnodes),
        idmove.ctypes.data_as(i32),
        int(ndsize),
        ncase_a.ctypes.data_as(i32),
        int(mtry),
        iv.ctypes.data_as(i32),
        nodeclass.ctypes.data_as(i32),
        ctypes.byref(ndbigtree),
        win_a.ctypes.data_as(f64),
        wr.ctypes.data_as(f64),
        wl.ctypes.data_as(f64),
        int(mdim),
        int(nuse),
        mind.ctypes.data_as(i32),
    )
    return {
        "treemap": treemap.tolist(),
        "bestvar": bestvar.tolist(),
        "bestsplit": bestsplit.tolist(),
        "bestsplitnext": bestsplitnext.tolist(),
        "tgini": tgini_a.tolist(),
        "nodestatus": nodestatus.tolist(),
        "nodeclass": nodeclass.tolist(),
        "ndbigtree": int(ndbigtree.value),
        "var_used": iv.tolist(),
        "order": a.tolist(),
    }


def _find_best_split(flat, jdex, y, mdim, nsample, ndstart, ndend, mtry, sumnode, node_count, cat):
    best_var = -1
    decsplit = 0.0
    best_split = 0.0
    best_for_all = 0.0
    value_at_best = 0.0
    var_indices = list(range(mdim))
    last = mdim - 1
    tie_var = 1
    ut = [0.0] * nsample
    xt = [0.0] * nsample
    yl = [0.0] * nsample
    tavcat = [0.0] * _MAX_CAT
    jstat = 0
    for _ in range(mtry):
        best_within = 0.0
        j = int(unif() * (last + 1))
        kv = var_indices[j]
        var_indices[j], var_indices[last] = var_indices[last], var_indices[j]
        last -= 1
        ncat = cat[kv]
        if ncat == 1:
            for j in range(ndstart, ndend + 1):
                xt[j] = flat[kv + (jdex[j] - 1) * mdim]
                yl[j] = y[jdex[j] - 1]
        else:
            counts = [0] * _MAX_CAT
            sums = [0.0] * _MAX_CAT
            for j in range(ndstart, ndend + 1):
                level = int(flat[kv + (jdex[j] - 1) * mdim])
                sums[level - 1] += y[jdex[j] - 1]
                counts[level - 1] += 1
            avcat = [sums[j] / counts[j] if counts[j] else 0.0 for j in range(ncat)]
            for j in range(nsample):
                level = int(flat[kv + (jdex[j] - 1) * mdim])
                xt[j] = avcat[level - 1]
                yl[j] = y[jdex[j] - 1]
        v = [0.0] * nsample
        for j in range(ndstart, ndend + 1):
            v[j] = xt[j]
        ncase = [j + 1 for j in range(nsample)]
        r_qsort_i(v, ncase, ndstart + 1, ndend + 1)
        if v[ndstart] >= v[ndend]:
            continue
        crit_parent = sumnode * sumnode / node_count
        suml = 0.0
        sumr = sumnode
        npopl = 0
        npopr = node_count
        tie_val = 1
        for j in range(ndstart, ndend):
            d = yl[ncase[j] - 1]
            suml += d
            sumr -= d
            npopl += 1
            npopr -= 1
            if v[j] < v[j + 1]:
                crit = (suml * suml / npopl) + (sumr * sumr / npopr) - crit_parent
                if crit > best_within:
                    value_at_best = (v[j] + v[j + 1]) / 2.0
                    best_within = crit
                    tie_val = 1
                if crit == best_within:
                    tie_val += 1
                    if unif() < 1.0 / tie_val:
                        value_at_best = (v[j] + v[j + 1]) / 2.0
                        best_within = crit
        if best_within > best_for_all:
            best_split = value_at_best
            best_var = kv + 1
            best_for_all = best_within
            for j in range(ndstart, ndend + 1):
                ut[j] = xt[j]
            if cat[kv] > 1:
                for j in range(cat[kv]):
                    tavcat[j] = avcat[j]
            tie_var = 1
        if best_within == best_for_all:
            tie_var += 1
            if unif() < 1.0 / tie_var:
                best_split = value_at_best
                best_var = kv + 1
                best_for_all = best_within
                for j in range(ndstart, ndend + 1):
                    ut[j] = xt[j]
                if cat[kv] > 1:
                    for j in range(cat[kv]):
                        tavcat[j] = avcat[j]
    decsplit = best_for_all
    ndendl = ndstart
    if best_var != -1:
        nl = ndstart
        for j in range(ndstart, ndend + 1):
            if ut[j] <= best_split:
                nl += 1
                ncase[nl - 1] = jdex[j]
        ndendl = max(nl - 1, ndstart)
        nr = ndendl + 1
        for j in range(ndstart, ndend + 1):
            if ut[j] > best_split:
                if nr >= nsample:
                    break
                nr += 1
                ncase[nr - 1] = jdex[j]
        if ndendl >= ndend:
            ndendl = ndend - 1
        for j in range(ndstart, ndend + 1):
            jdex[j] = ncase[j]
        ncat = cat[best_var - 1]
        if ncat > 1:
            icat = [1 if tavcat[j] < best_split else 0 for j in range(ncat)]
            packed = float(icat[ncat - 1])
            for bit in range(ncat - 2, -1, -1):
                packed = 2.0 * packed + icat[bit]
            best_split = packed
    else:
        jstat = _NODE_TERMINAL
    return best_var, decsplit, best_split, ndendl, jstat


def _reg_tree(flat, y, mdim, nsample, nrnodes, nthsize, mtry, cat, tgini):
    nodestatus = [0] * nrnodes
    nodestart = [0] * nrnodes
    counts = [0] * nrnodes
    means = [0.0] * nrnodes
    left = [0] * nrnodes
    right = [0] * nrnodes
    bestvar = [0] * nrnodes
    upper = [0.0] * nrnodes
    var_used = [0] * mdim
    jdex = [i + 1 for i in range(nsample)]
    current = 0
    nodestart[0] = 0
    counts[0] = nsample
    nodestatus[0] = _NODE_TOSPLIT
    node_mean = 0.0
    for i in range(nsample):
        label = y[jdex[i] - 1]
        node_mean = (i * node_mean + label) / (i + 1)
    means[0] = node_mean
    for k in range(nrnodes - 2):
        if k > current or current >= nrnodes - 2:
            break
        if nodestatus[k] != _NODE_TOSPLIT:
            continue
        ndstart = nodestart[k]
        ndend = ndstart + counts[k] - 1
        node_count = counts[k]
        sum_node = node_count * means[k]
        msplit, decsplit, ubest, ndendl, jstat = _find_best_split(
            flat, jdex, y, mdim, nsample, ndstart, ndend, mtry, sum_node, node_count, cat
        )
        if jstat == _NODE_TERMINAL:
            nodestatus[k] = jstat
            continue
        bestvar[k] = msplit
        var_used[msplit - 1] = 1
        upper[k] = ubest
        tgini[msplit - 1] += decsplit
        nodestatus[k] = _NODE_INTERIOR
        counts[current + 1] = ndendl - ndstart + 1
        counts[current + 2] = ndend - ndendl
        nodestart[current + 1] = ndstart
        nodestart[current + 2] = ndendl + 1
        node_mean = 0.0
        for j in range(ndstart, ndendl + 1):
            label = y[jdex[j] - 1]
            m = j - ndstart
            node_mean = (m * node_mean + label) / (m + 1)
        means[current + 1] = node_mean
        nodestatus[current + 1] = _NODE_TOSPLIT
        if counts[current + 1] <= nthsize:
            nodestatus[current + 1] = _NODE_TERMINAL
        node_mean = 0.0
        for j in range(ndendl + 1, ndend + 1):
            label = y[jdex[j] - 1]
            m = j - (ndendl + 1)
            node_mean = (m * node_mean + label) / (m + 1)
        means[current + 2] = node_mean
        nodestatus[current + 2] = _NODE_TOSPLIT
        if counts[current + 2] <= nthsize:
            nodestatus[current + 2] = _NODE_TERMINAL
        left[k] = current + 2
        right[k] = current + 3
        current += 2
    tree_size = nrnodes
    for k in range(nrnodes - 1, -1, -1):
        if nodestatus[k] == 0:
            tree_size -= 1
        if nodestatus[k] == _NODE_TOSPLIT:
            nodestatus[k] = _NODE_TERMINAL
    return left, right, upper, means, nodestatus, tree_size, bestvar, var_used


def _predict_reg_tree(flat, nsample, mdim, left, right, nodestatus, split, nodepred, split_var, tree_size, cat, maxcat):
    decoded = None
    if maxcat > 1:
        decoded = [0] * (maxcat * tree_size)
        for i in range(tree_size):
            if nodestatus[i] != _NODE_TERMINAL and cat[split_var[i] - 1] > 1:
                packed = split[i]
                for j in range(cat[split_var[i] - 1]):
                    decoded[j + i * maxcat] = 1 if (int(packed) & 1) else 0
                    packed /= 2.0
    ypred = [0.0] * nsample
    nodex = [0] * nsample
    for i in range(nsample):
        k = 0
        while nodestatus[k] != _NODE_TERMINAL:
            m = split_var[k] - 1
            if cat[m] == 1:
                k = left[k] - 1 if flat[m + i * mdim] <= split[k] else right[k] - 1
            else:
                bit = decoded[int(flat[m + i * mdim]) - 1 + k * maxcat]
                k = left[k] - 1 if bit else right[k] - 1
        ypred[i] = nodepred[k]
        nodex[i] = k + 1
    return ypred, nodex


def _flatten(matrix):
    rows, cols = matrix.shape
    flat = [0.0] * (rows * cols)
    for case in range(rows):
        for var in range(cols):
            flat[var + case * cols] = float(matrix[case, var])
    return flat


def _class_forest(x, y_codes, nclass, cat, ntree, mtry, nodesize, nrnodes, cutoff, classwt, ipi, replace, sampsize, keep_forest, importance, maxcat, local_imp=False, proximity=False, oob_prox=True):
    nsample, mdim = x.shape
    flat = _flatten(x)
    class_freq = [0] * nclass
    for label in y_codes:
        class_freq[label - 1] += 1
    classwt = _norm_class_wt(nsample, nclass, ipi, classwt, class_freq)
    order0, ranks = _make_a(flat, mdim, nsample, cat)
    counttr = [0] * (nclass * nsample)
    out = [0] * nsample
    tgini = [0.0] * mdim
    errtr = [0.0] * ((nclass + 1) * ntree)
    ndbigtree = [0] * ntree
    keep_status = []
    keep_best = []
    keep_map = []
    keep_class = []
    keep_split = []
    outcl = [0] * nsample
    imprt = [0.0] * ((nclass + 2) * mdim)
    impsd = [0.0] * ((nclass + 1) * mdim)
    prox = [0.0] * (nsample * nsample) if proximity else None
    pairs = [0] * (nsample * nsample) if proximity else None
    for jb in range(ntree):
        while True:
            inbag = [0] * nsample
            tclasspop = [0.0] * nclass
            win = [0.0] * nsample
            ntry = 0
            while True:
                ntry += 1
                inbag = [0] * nsample
                tclasspop = [0.0] * nclass
                win = [0.0] * nsample
                sampled = _sample_rows(nsample, sampsize, replace)
                for index in sampled:
                    tclasspop[y_codes[index] - 1] += classwt[y_codes[index] - 1]
                    win[index] += classwt[y_codes[index] - 1]
                    inbag[index] += 1
                empty = sum(1 for value in tclasspop if value == 0.0)
                if nclass - empty >= 2 or ntry > 30:
                    break
            if nclass - sum(1 for value in tclasspop if value == 0.0) < 2:
                raise RuntimeError("Still have fewer than two classes in the in-bag sample after 30 attempts.")
            order = order0[:]
            nuse, ncase = _mod_a(order, nsample, mdim, cat, maxcat, inbag)
            grown = _buildtree(
                order, ranks, y_codes, cat, maxcat, mdim, nsample, nclass, nrnodes,
                nodesize, ncase, mtry, nuse, win, tclasspop, tgini,
            )
            tgini = grown["tgini"]
            if grown["ndbigtree"] != 1:
                break
        tree_size = grown["ndbigtree"]
        ndbigtree[jb] = tree_size
        xbest = [0.0] * nrnodes
        _xtranslate(flat, mdim, grown["bestvar"], grown["bestsplit"], grown["bestsplitnext"], grown["nodestatus"], cat, tree_size, xbest)
        jtr, nodes = _predict_class_tree(
            flat, nsample, mdim, grown["treemap"], grown["nodestatus"], xbest,
            grown["bestvar"], grown["nodeclass"], tree_size, cat, maxcat,
        )
        for n in range(nsample):
            if inbag[n] == 0:
                counttr[n * nclass + jtr[n] - 1] += 1
                out[n] += 1
        nout = [0] * nclass
        for n in range(nsample):
            if inbag[n] == 0:
                nout[y_codes[n] - 1] += 1
        noutall = sum(nout)
        jest, err = _oob(nsample, nclass, y_codes, jtr, counttr, out, cutoff)
        outcl = jest
        errtr[jb * (nclass + 1):(jb + 1) * (nclass + 1)] = err
        if proximity:
            _accumulate_proximity(prox, pairs, nodes, inbag, nsample, oob_prox)
        if importance:
            nright = [0] * nclass
            nrightall = 0
            for n in range(nsample):
                if inbag[n] == 0 and jtr[n] == y_codes[n]:
                    nright[y_codes[n] - 1] += 1
                    nrightall += 1
            for m in range(mdim):
                if grown["var_used"][m]:
                    saved = [flat[m + n * mdim] for n in range(nsample)]
                    _permute_oob(m, flat, inbag, nsample, mdim)
                    jvr, _nodes = _predict_class_tree(
                        flat, nsample, mdim, grown["treemap"], grown["nodestatus"], xbest,
                        grown["bestvar"], grown["nodeclass"], tree_size, cat, maxcat,
                    )
                    nrightimp = [0] * nclass
                    nrightimpall = 0
                    for n in range(nsample):
                        flat[m + n * mdim] = saved[n]
                        if inbag[n] == 0 and jvr[n] == y_codes[n]:
                            nrightimp[y_codes[n] - 1] += 1
                            nrightimpall += 1
                    for ncls in range(nclass):
                        if nout[ncls] > 0:
                            delta = (nright[ncls] - nrightimp[ncls]) / nout[ncls]
                            imprt[m + ncls * mdim] += delta
                            impsd[m + ncls * mdim] += delta * delta
                    if noutall > 0:
                        delta = (nrightall - nrightimpall) / noutall
                        imprt[m + nclass * mdim] += delta
                        impsd[m + nclass * mdim] += delta * delta
        if keep_forest:
            keep_status.append(grown["nodestatus"])
            keep_best.append(grown["bestvar"])
            keep_map.append(grown["treemap"])
            keep_class.append(grown["nodeclass"])
            keep_split.append(xbest)
    for m in range(mdim):
        tgini[m] /= ntree
    if importance:
        for m in range(mdim):
            for k in range(nclass + 1):
                average = imprt[m + k * mdim] / ntree
                impsd[m + k * mdim] = math.sqrt(((impsd[m + k * mdim] / ntree) - average * average) / ntree)
                imprt[m + k * mdim] = average
            imprt[m + (nclass + 1) * mdim] = tgini[m]
    else:
        for m in range(mdim):
            imprt[m] = tgini[m]
    return {
        "outcl": outcl,
        "counttr": counttr,
        "errtr": errtr,
        "tgini": tgini,
        "imprt": imprt,
        "impsd": impsd,
        "ndbigtree": ndbigtree,
        "nodestatus": keep_status,
        "bestvar": keep_best,
        "treemap": keep_map,
        "nodeclass": keep_class,
        "xbestsplit": keep_split,
        "classwt": classwt,
        "oob_times": out,
        "nrnodes": nrnodes,
        "proximity": _finish_proximity(prox, pairs, nsample, ntree, oob_prox) if proximity else None,
    }


def _accumulate_proximity(prox, pairs, nodes, inbag, n, oob_prox):
    for i in range(n):
        for j in range(i + 1, n):
            if oob_prox:
                if inbag[i] > 0 or inbag[j] > 0:
                    continue
                pairs[j * n + i] += 1
                pairs[i * n + j] += 1
            if nodes[i] == nodes[j]:
                prox[j * n + i] += 1.0
                prox[i * n + j] += 1.0


def _finish_proximity(prox, pairs, n, ntree, oob_prox):
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if oob_prox:
                count = pairs[j * n + i]
                denom = count if count > 0 else 1
            else:
                denom = ntree
            value = prox[j * n + i] / denom
            matrix[i][j] = value
            matrix[j][i] = value
        matrix[i][i] = 1.0
    return matrix


def _reg_forest(x, y, cat, ntree, mtry, nodesize, nrnodes, replace, sampsize, keep_forest, importance, maxcat, n_perm, proximity=False, oob_prox=True):
    nsample, mdim = x.shape
    flat = _flatten(x)
    y = [float(item) for item in y]
    yptr = [0.0] * nsample
    nout = [0] * nsample
    mse = [0.0] * ntree
    tgini = [0.0] * mdim
    errimp = [0.0] * mdim
    imp_sd = [0.0] * mdim
    trees = []
    prox = [0.0] * (nsample * nsample) if proximity else None
    pairs = [0] * (nsample * nsample) if proximity else None
    for j in range(ntree):
        inbag = [0] * nsample
        var_used = [0] * mdim
        sampled = _sample_rows(nsample, sampsize, replace)
        yb = [0.0] * sampsize
        xb = [0.0] * (mdim * sampsize)
        for n, k in enumerate(sampled):
            inbag[k] += 1
            yb[n] = y[k]
            for m in range(mdim):
                xb[m + n * mdim] = flat[m + k * mdim]
        left, right, upper, means, status, tree_size, bestvar, var_used = _reg_tree(
            xb, yb, mdim, sampsize, nrnodes, nodesize, mtry, cat, tgini
        )
        ytr, nodex = _predict_reg_tree(
            flat, nsample, mdim, left, right, status, upper, means, bestvar, tree_size, cat, maxcat
        )
        errb = 0.0
        ooberr = 0.0
        jout = 0
        n_oob = 0
        res_oob = [0.0] * nsample
        for n in range(nsample):
            if inbag[n] == 0:
                nout[n] += 1
                n_oob += 1
                yptr[n] = ((nout[n] - 1) * yptr[n] + ytr[n]) / nout[n]
                res_oob[n] = ytr[n] - y[n]
                ooberr += res_oob[n] * res_oob[n]
            if nout[n]:
                jout += 1
                errb += (y[n] - yptr[n]) * (y[n] - yptr[n])
        errb /= jout
        mse[j] = errb
        if proximity:
            _accumulate_proximity(prox, pairs, nodex, inbag, nsample, oob_prox)
        if importance:
            original = flat[:]
            for mr in range(mdim):
                if var_used[mr]:
                    saved = [flat[mr + n * mdim] for n in range(nsample)]
                    ooberrperm = 0.0
                    for _k in range(n_perm):
                        _permute_oob(mr, flat, inbag, nsample, mdim)
                        yhat, _ = _predict_reg_tree(
                            flat, nsample, mdim, left, right, status, upper, means, bestvar, tree_size, cat, maxcat
                        )
                        for n in range(nsample):
                            if inbag[n] == 0:
                                r = yhat[n] - y[n]
                                ooberrperm += r * r
                    delta = (ooberrperm / n_perm - ooberr) / n_oob
                    errimp[mr] += delta
                    imp_sd[mr] += delta * delta
                    for n in range(nsample):
                        flat[mr + n * mdim] = saved[n]
            flat = original
        if keep_forest:
            trees.append({
                "left": left, "right": right, "upper": upper, "means": means,
                "status": status, "size": tree_size, "bestvar": bestvar,
            })
    if importance:
        for m in range(mdim):
            errimp[m] /= ntree
            imp_sd[m] = math.sqrt(((imp_sd[m] / ntree) - errimp[m] * errimp[m]) / ntree)
    for m in range(mdim):
        tgini[m] /= ntree
    return {
        "yptr": yptr,
        "mse": mse,
        "nout": nout,
        "tgini": tgini,
        "errimp": errimp,
        "imp_sd": imp_sd,
        "trees": trees,
        "nrnodes": nrnodes,
        "proximity": _finish_proximity(prox, pairs, nsample, ntree, oob_prox) if proximity else None,
    }


class RandomForest:
    """A fitted forest. Fields follow the R ``randomForest`` list."""

    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __getitem__(self, key):
        return getattr(self, key)


def random_forest(
    x,
    y,
    ntree=500,
    mtry=None,
    replace=True,
    classwt=None,
    cutoff=None,
    sampsize=None,
    nodesize=None,
    maxnodes=None,
    importance=False,
    local_imp=False,
    n_perm=1,
    proximity=False,
    oob_prox=None,
    norm_votes=True,
    do_trace=False,
    keep_forest=True,
    corr_bias=False,
    keep_inbag=False,
    xtest=None,
    ytest=None,
):
    """Fit a forest. ``y`` labels make a classification forest; numbers make regression."""
    del do_trace, local_imp, xtest, ytest, corr_bias, keep_inbag
    if oob_prox is None:
        oob_prox = bool(proximity)
    proximity = bool(proximity)
    matrix = _as_matrix(x)
    n, p = matrix.shape
    if mtry is None:
        numeric = not isinstance(y[0], str)
        try:
            sample = list(y)
        except TypeError:
            sample = [y]
        looks_class = any(isinstance(item, str) for item in sample)
        mtry = max(math.floor(p / 3), 1) if not looks_class else math.floor(math.sqrt(p))
    mtry = max(1, min(p, _r_round(mtry)))
    if sampsize is None:
        sampsize = n if replace else math.ceil(0.632 * n)
    sampsize = int(sampsize)
    labels = list(y)
    class_fit = any(isinstance(item, str) for item in labels) or (
        labels and not isinstance(labels[0], (int, float)) or (isinstance(labels[0], int) and not isinstance(labels[0], bool) and len(set(labels)) <= 5 and False)
    )
    # Classification when the caller passes labels that are not plain floats.
    if labels and isinstance(labels[0], str):
        class_fit = True
    elif labels and isinstance(labels[0], (int, np.integer)) and not isinstance(labels[0], bool):
        class_fit = False
    else:
        class_fit = False
    if nodesize is None:
        nodesize = 1 if class_fit else 5
    nodesize = int(nodesize)
    if class_fit:
        codes, levels = _factor(labels)
        nclass = len(levels)
        if cutoff is None:
            cutoff = [1.0 / nclass] * nclass
        if classwt is None:
            classwt = [1.0] * nclass
            ipi = 0
        else:
            ipi = 1
        nrnodes = 2 * sampsize + 1
        if maxnodes is not None:
            maxnodes = 2 * int(maxnodes) - 1
            nrnodes = min(nrnodes, max(maxnodes, 1))
        cat = [1] * p
        maxcat = 1
        grown = _class_forest(
            matrix, codes, nclass, cat, int(ntree), mtry, nodesize, nrnodes,
            [float(item) for item in cutoff], [float(item) for item in classwt],
            ipi, bool(replace), sampsize, bool(keep_forest), bool(importance), maxcat,
            proximity=proximity, oob_prox=bool(oob_prox),
        )
        votes = []
        oob_times = []
        for row in range(n):
            counts = [grown["counttr"][row * nclass + col] for col in range(nclass)]
            total = sum(counts)
            oob_times.append(total)
            if norm_votes:
                votes.append([item / total if total else math.nan for item in counts])
            else:
                votes.append(counts)
        predicted = []
        for code in grown["outcl"]:
            predicted.append(levels[code - 1] if code else None)
        err = []
        for tree in range(int(ntree)):
            err.append(grown["errtr"][tree * (nclass + 1):(tree + 1) * (nclass + 1)])
        names = [f"x{i + 1}" for i in range(p)]
        if hasattr(x, "columns"):
            names = [str(item) for item in list(x.columns)]
        if importance:
            importance_matrix = [
                [grown["imprt"][m + k * p] for k in range(nclass + 2)] for m in range(p)
            ]
            importance_sd = [
                [grown["impsd"][m + k * p] for k in range(nclass + 1)] for m in range(p)
            ]
        else:
            importance_matrix = [[grown["tgini"][m]] for m in range(p)]
            importance_sd = None
        forest = None
        if keep_forest:
            biggest = max(grown["ndbigtree"])
            status = []
            best = []
            pred = []
            split = []
            treemap = []
            for node in range(biggest):
                status.append([grown["nodestatus"][tree][node] for tree in range(int(ntree))])
                best.append([grown["bestvar"][tree][node] for tree in range(int(ntree))])
                pred.append([grown["nodeclass"][tree][node] for tree in range(int(ntree))])
                split.append([grown["xbestsplit"][tree][node] for tree in range(int(ntree))])
                pair = []
                for tree in range(int(ntree)):
                    pair.append([grown["treemap"][tree][node * 2], grown["treemap"][tree][node * 2 + 1]])
                treemap.append(pair)
            forest = {
                "ndbigtree": grown["ndbigtree"],
                "nodestatus": status,
                "bestvar": best,
                "treemap": treemap,
                "nodepred": pred,
                "xbestsplit": split,
                "pid": grown["classwt"],
                "cutoff": list(cutoff),
                "ncat": cat,
                "maxcat": maxcat,
                "nrnodes": biggest,
                "ntree": int(ntree),
                "nclass": nclass,
                "xlevels": [0] * p,
            }
        return RandomForest(
            type="classification",
            predicted=predicted,
            err_rate=err,
            votes=votes,
            oob_times=oob_times,
            classes=levels,
            importance=importance_matrix,
            importance_sd=importance_sd,
            ntree=int(ntree),
            mtry=mtry,
            forest=forest,
            y=labels,
            proximity=grown["proximity"],
            inbag=None,
            test=None,
            x_names=names,
            _x=matrix.copy(),
            _nodesize=nodesize,
        )
    y_values = [float(item) for item in labels]
    y_mean = sum(y_values) / n
    centered = [item - y_mean for item in y_values]
    nrnodes = 2 * sampsize + 1
    if maxnodes is not None:
        maxnodes = 2 * int(maxnodes) - 1
        nrnodes = min(nrnodes, max(maxnodes, 1))
    cat = [1] * p
    maxcat = 1
    grown = _reg_forest(
        matrix, centered, cat, int(ntree), mtry, nodesize, nrnodes, bool(replace),
        sampsize, bool(keep_forest), bool(importance), maxcat, int(n_perm),
        proximity=proximity, oob_prox=bool(oob_prox),
    )
    predicted = []
    for i, value in enumerate(grown["yptr"]):
        if grown["nout"][i] == 0:
            predicted.append(float("nan"))
        else:
            predicted.append(value + y_mean)
    var = sum((item - y_mean) ** 2 for item in y_values) / (n - 1)
    scale = var * (n - 1) / n
    rsq = [1.0 - item / scale for item in grown["mse"]]
    names = [f"x{i + 1}" for i in range(p)]
    if importance:
        importance_matrix = [[grown["errimp"][m], grown["tgini"][m]] for m in range(p)]
        importance_sd = grown["imp_sd"]
    else:
        importance_matrix = [[grown["tgini"][m]] for m in range(p)]
        importance_sd = None
    forest = None
    if keep_forest and grown["trees"]:
        biggest = max(tree["size"] for tree in grown["trees"])
        def columns(key):
            return [[tree[key][node] if node < len(tree[key]) else 0 for tree in grown["trees"]] for node in range(biggest)]
        means = []
        for node in range(biggest):
            means.append([
                (tree["means"][node] + y_mean) if node < tree["size"] else y_mean
                for tree in grown["trees"]
            ])
        forest = {
            "ndbigtree": [tree["size"] for tree in grown["trees"]],
            "nodestatus": columns("status"),
            "left_daughter": columns("left"),
            "right_daughter": columns("right"),
            "nodepred": means,
            "bestvar": columns("bestvar"),
            "xbestsplit": columns("upper"),
            "ncat": cat,
            "nrnodes": biggest,
            "ntree": int(ntree),
            "xlevels": [0] * p,
        }
    return RandomForest(
        type="regression",
        predicted=predicted,
        mse=grown["mse"],
        rsq=rsq,
        oob_times=grown["nout"],
        importance=importance_matrix,
        importance_sd=importance_sd,
        proximity=grown["proximity"],
        ntree=int(ntree),
        mtry=mtry,
        forest=forest,
        y=y_values,
        coefs=None,
        test=None,
        inbag=None,
        classes=None,
        votes=None,
        err_rate=None,
        x_names=names,
        _x=matrix.copy(),
        _nodesize=nodesize,
    )
