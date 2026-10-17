"""Translation of permute's shuffleSeries (R/shuffle-utils.R).

A line transect is a cyclic shift of ``1..n`` starting at ``start``. With
``mirror`` the shift is reversed on a coin flip (``flip``, or ``runif(1) < 0.5``
when ``flip`` is not given). The result indexes ``x`` with R's 1-based values.
"""

from __future__ import annotations

import numpy as np

from ._rng import unif_rand
from ._shuffle_common import as_flag
from .shuffleFree import shuffleFree


def shuffleSeries(x, mirror=False, start=None, flip=None):
    a = np.atleast_1d(np.asarray(x))
    n = len(a)
    if start is None:
        start = int(shuffleFree(n, 1)[0])
    # R: out <- seq(start, length = n) %% n + 1, used as 1-based indices into x
    out = np.arange(int(start), int(start) + n) % n + 1
    if flip is not None and mirror:
        if as_flag(flip):
            out = out[::-1]
    else:
        if mirror and unif_rand() < 0.5:
            out = out[::-1]
    return a[out - 1]
