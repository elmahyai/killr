"""Translation of permute's shuffleSet (R/shuffleSet.R, with doShuffleSet).

``shuffleSet(n, nset, control)`` returns a matrix with one permutation of
``1..n`` per row (1-based, as R returns it). When ``check`` is true the design
is checked first (``check``); if the design has few enough permutations for
complete enumeration, the rows are sampled from all permutations.
"""

from __future__ import annotations

from copy import deepcopy

import numpy as np

from ._rng import sample_int, unif_rand
from ._shuffle_common import levels_of, n_of
from .check import check as _check
from .core import How, how as _core_how
from .shuffleFree import shuffleFree
from .shuffleGrid import shuffleGrid
from .shuffleSeries import shuffleSeries
from .shuffleStrata import shuffleStrata


def _as_how(control):
    return control if isinstance(control, How) else _core_how()


def _do_shuffle_set(ind, nset, control):
    """R's doShuffleSet: an nset-by-length(ind) matrix of 1-based observations."""
    n = len(ind)
    sn = np.arange(1, n + 1)
    within = control.within
    type_w = within.type
    strata = control.plots.strata
    s = np.zeros((nset, n), dtype=int)

    if strata is None:
        if type_w == "none":
            s[:, :] = sn
        else:
            for i in range(nset):
                if type_w == "free":
                    s[i] = shuffleFree(n, n)
                elif type_w == "series":
                    s[i] = shuffleSeries(sn, mirror=within.mirror)
                elif type_w == "grid":
                    s[i] = shuffleGrid(nrow=within.nrow, ncol=within.ncol, mirror=within.mirror)
        return ind[s - 1]

    full = np.ravel(np.asarray(strata))
    levels = levels_of(full)  # getStrata(drop = TRUE) keeps every level
    pstrata = full[ind - 1]
    type_p = control.plots.type
    plots = control.plots

    if type_p == "none":
        s[:, :] = sn
    else:
        for i in range(nset):
            s[i] = shuffleStrata(pstrata, type=type_p, mirror=plots.mirror, flip=None,
                                 nrow=plots.nrow, ncol=plots.ncol)

    tmp = s.copy()
    if type_w != "none":
        for i in range(nset):
            row = s[i]
            pv = pstrata[row - 1]  # Pstrata[ind][Set[i, ]]
            counts = [int(np.count_nonzero(pv == lv)) for lv in levels]
            constant = within.constant

            start = start_row = start_col = flip = None
            same_rand = None
            if constant:
                if type_w == "free":
                    big_n = counts[0]  # unique(tab)[1]
                    same_rand = shuffleFree(big_n, big_n)
                elif type_w == "series":
                    start = shuffleFree(n / len(levels), 1)[0]
                    flip = unif_rand() < 0.5
                elif type_w == "grid":
                    start_row = shuffleFree(within.nrow, 1)[0]
                    start_col = shuffleFree(within.ncol, 1)[0]
                    flip = [unif_rand() < 0.5, unif_rand() < 0.5]

            for lv in levels:
                match = pv == lv
                gr = row[match]
                n_gr = len(gr)
                if n_gr > 1:
                    if constant and type_w == "free":
                        tmp[i, match] = gr[same_rand - 1]
                    else:
                        if type_w == "free":
                            idx = shuffleFree(n_gr, n_gr)
                        elif type_w == "series":
                            idx = shuffleSeries(np.arange(1, n_gr + 1), mirror=within.mirror,
                                                start=start, flip=flip)
                        else:
                            idx = shuffleGrid(nrow=within.nrow, ncol=within.ncol,
                                              mirror=within.mirror, start_row=start_row,
                                              start_col=start_col, flip=flip)
                        tmp[i, match] = gr[idx - 1]
        s = tmp
    return ind[s - 1]


def shuffleSet(n, nset=None, control=None, check=True, quietly=False):
    control = deepcopy(_as_how(control))  # R works on a local copy of control

    # missing(nset): take nperm from the control; otherwise setNperm(control) <- nset
    if nset is None:
        nset = control.nperm if control.nperm is not None else 1
    else:
        control.nperm = int(nset)

    N = n_of(n)
    sn = np.arange(1, N + 1)

    if check:
        all_orig = control.complete
        result = _check(sn, control, quietly=quietly)
        control = result["control"]
        if all_orig:
            nset = control.nperm

    all_perms = control.all_perms
    if all_perms is None:
        block = control.blocks
        if block is None:
            block = np.ones(N, dtype=int)  # factor(rep(1, n))
        else:
            block = np.ravel(np.asarray(block))
        levels = levels_of(block)
        groups = [sn[block == lv] for lv in levels]
        parts = [_do_shuffle_set(g, nset, control) for g in groups]
        out = np.empty((nset, N), dtype=int)
        out[:, np.concatenate(groups) - 1] = np.hstack(parts)  # out[, unlist(spln)] <- out
    else:
        out = np.asarray(all_perms, dtype=int)

    nr = out.shape[0]
    if nr > nset:
        rows = np.asarray(sample_int(nr, nset, replace=False), dtype=int)
        out = out[rows - 1, :]
    return out
