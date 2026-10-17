"""Translation of permute's shuffleStrata (R/shuffle-utils.R).

Whole strata are permuted as a unit: the levels of ``strata`` (unused levels
dropped, sorted) are reordered by a free, series, or grid permutation, and
each level takes the observations of the level it is moved to. The result is
the 1-based observation index for each position, as R returns it.
"""

from __future__ import annotations

import numpy as np

from ._shuffle_common import levels_of
from .shuffleFree import shuffleFree
from .shuffleGrid import shuffleGrid
from .shuffleSeries import shuffleSeries


def shuffleStrata(strata, type, mirror=False, start=None, flip=None,
                  nrow=None, ncol=None, start_row=None, start_col=None):
    vals = np.ravel(np.asarray(strata))
    levels = levels_of(vals)
    lev = len(levels)
    seq = np.arange(1, lev + 1)
    if type == "free":
        perm = shuffleFree(lev, lev)
    elif type == "series":
        perm = shuffleSeries(seq, mirror=mirror, start=start, flip=flip)
    elif type == "grid":
        perm = shuffleGrid(nrow=nrow, ncol=ncol, mirror=mirror,
                           start_row=start_row, start_col=start_col, flip=flip)
    else:
        raise ValueError("Invalid permutation type.")
    out = np.arange(1, len(vals) + 1)
    # R: sp <- split(seq_along(strata), strata); the 1-based positions of each level
    positions = {lv: np.flatnonzero(vals == lv) + 1 for lv in levels}
    for i in range(lev):
        want = np.flatnonzero(vals == levels[i]) + 1
        out[want - 1] = positions[levels[int(perm[i]) - 1]]
    return out
