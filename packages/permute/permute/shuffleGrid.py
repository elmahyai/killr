"""Translation of permute's shuffleGrid (R/shuffle-utils.R).

A grid is shifted by ``start_row`` and ``start_col`` (drawn with ``shuffleFree``
when not given) and, with ``mirror``, its rows and columns are reversed on
``flip`` (or on ``runif`` draws when ``flip`` is not given). The result is the
1-based cell index of each position in the ``nrow * ncol`` grid, filled by
column, as R returns it.
"""

from __future__ import annotations

import numpy as np

from ._rng import unif_rand
from .shuffleFree import shuffleFree


def shuffleGrid(nrow, ncol, mirror=False, start_row=None, start_col=None, flip=None):
    nrow, ncol = int(nrow), int(ncol)
    if start_row is None:
        start_row = int(shuffleFree(nrow, 1)[0])
    if start_col is None:
        start_col = int(shuffleFree(ncol, 1)[0])
    # R: ir <- seq(start.row, length = nrow) %% nrow (0-based here)
    ir = np.arange(int(start_row), int(start_row) + nrow) % nrow
    ic = np.arange(int(start_col), int(start_col) + ncol) % ncol
    if flip is not None and mirror:
        f = np.ravel(np.asarray(flip, dtype=bool))
        if np.any(f):
            if f.size < 2:
                raise ValueError("flip needs two values when mirror = TRUE")
            if f[0]:
                ir = ir[::-1]
            if f[1]:
                ic = ic[::-1]
    else:
        if mirror:
            if unif_rand() < 0.5:
                ir = ir[::-1]
            if unif_rand() < 0.5:
                ic = ic[::-1]
    # R: rep(ic, each = nrow) * nrow + rep(ir, len = nrow * ncol) + 1
    return np.repeat(ic, nrow) * nrow + np.tile(ir, ncol) + 1
