"""Translation of permute's shuffle (R/shuffle.R, with doShuffle and shuffleNoStrata).

``shuffle(n, control)`` returns one permutation of ``1..n`` (1-based, as R
returns it) that respects the blocks, plot strata, and within-plot design in
``control``. Blocks are shuffled separately and put back in place. Random
draws come from R's stream in R's order, so ``set_seed`` gives R's result.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ._rng import unif_rand
from ._shuffle_common import levels_of, n_of
from .core import How, how as _core_how
from .shuffleFree import shuffleFree
from .shuffleGrid import shuffleGrid
from .shuffleSeries import shuffleSeries
from .shuffleStrata import shuffleStrata


def _as_how(control):
    return control if isinstance(control, How) else _core_how()


def _shuffle_no_strata(n, control):
    """R's shuffleNoStrata."""
    t = control.within.type
    if t == "free":
        return shuffleFree(n, n)
    if t == "series":
        return shuffleSeries(np.arange(1, n + 1), mirror=control.within.mirror)
    if t == "grid":
        return shuffleGrid(nrow=control.within.nrow, ncol=control.within.ncol,
                           mirror=control.within.mirror)
    if t == "none":
        return np.arange(1, n + 1)
    raise ValueError("Invalid permutation type")


def _first_unique(counts):
    """R's unique(tab)[1]: the first count in order of appearance."""
    return counts[0]


def _do_shuffle(ind, control):
    """R's doShuffle. ``ind`` holds the 1-based observations of one block."""
    n = len(ind)
    sn = np.arange(1, n + 1)
    strata = control.plots.strata

    # no strata at plot level: permute every sample with the within scheme
    if strata is None:
        perm = _shuffle_no_strata(n, control)
        return ind[perm - 1]

    full = np.ravel(np.asarray(strata))
    levels = levels_of(full)  # getStrata(drop = TRUE) keeps every level
    pstrata = full[ind - 1]
    type_p = control.plots.type
    type_w = control.within.type

    if type_p == "none":
        perm = sn
    else:
        flip = unif_rand() < 0.5  # runif(1L) < 0.5, drawn before shuffleStrata
        perm = shuffleStrata(pstrata, type=type_p, mirror=control.plots.mirror,
                             flip=flip, nrow=control.plots.nrow, ncol=control.plots.ncol)

    if type_w != "none":
        pv = pstrata[perm - 1]
        counts = [int(np.count_nonzero(pv == lv)) for lv in levels]  # table(Pstrata[perm])
        within = control.within
        constant = within.constant

        start = start_row = start_col = flip = None
        same_rand = None
        if constant:
            if type_w == "free":
                big_n = _first_unique(counts)
                same_rand = shuffleFree(big_n, big_n)
            elif type_w == "series":
                start = shuffleFree(n / len(levels), 1)[0]
                flip = unif_rand() < 0.5
            elif type_w == "grid":
                start_row = shuffleFree(within.nrow, 1)[0]
                start_col = shuffleFree(within.ncol, 1)[0]
                flip = [unif_rand() < 0.5, unif_rand() < 0.5]

        tmp = perm.copy()
        for lv in levels:
            match = pv == lv
            gr = perm[match]
            n_gr = len(gr)
            if n_gr > 1:
                if type_w == "free":
                    if constant:
                        sel = gr[same_rand - 1]
                    else:
                        sel = gr[shuffleFree(n_gr, n_gr) - 1]
                elif type_w == "series":
                    sel = gr[shuffleSeries(np.arange(1, n_gr + 1), mirror=within.mirror,
                                           start=start, flip=flip) - 1]
                elif type_w == "grid":
                    sel = gr[shuffleGrid(nrow=within.nrow, ncol=within.ncol,
                                         mirror=within.mirror, start_row=start_row,
                                         start_col=start_col, flip=flip) - 1]
                else:
                    raise ValueError("Invalid permutation type")
                tmp[match] = sel
        perm = tmp
    return ind[perm - 1]


def shuffle(n, control=None):
    control = _as_how(control)
    N = n_of(n)
    sn = np.arange(1, N + 1)

    if control.blocks is None:
        block = np.ones(N, dtype=int)  # factor(rep(1, n))
    else:
        block = np.ravel(np.asarray(control.blocks))
        control = replace(control, blocks=None)  # update(control, blocks = NULL)

    out = np.empty(N, dtype=int)
    for lv in levels_of(block):
        where = block == lv
        out[where] = _do_shuffle(sn[where], control)  # unsplit(out, Block)
    return out
