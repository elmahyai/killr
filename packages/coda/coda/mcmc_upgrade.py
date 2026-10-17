"""Upgrade pre-0.4 three-dimensional mcmc objects.

Translated from coda 0.19-4.1 ``mcmcUpgrade`` in ``R/mcmc.R``.
"""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import Mcmc, as_mcmc
from coda.as_mcmc_list import as_mcmc_list


def mcmc_upgrade(x):
    """Convert an obsolete three-dimensional ``mcmc`` layout to modern chains."""
    if not isinstance(x, Mcmc):
        raise ValueError("Can't upgrade")

    array = np.asarray(x.data)
    if array.ndim != 3:
        return x

    if x.tspar is not None:
        tspar = np.asarray(x.tspar, dtype=np.float64).reshape(-1)
        xstart, xend, xthin = (float(tspar[0]), float(tspar[1]), float(tspar[2]))
    else:
        xstart, xend, xthin = x.start, x.end, x.thin

    nchain = int(array.shape[2])
    out = []
    for _i in range(nchain):
        # R ``mcmcUpgrade`` always slices chain dimension index 1 (see ``R/mcmc.R``).
        y = np.asarray(array[:, :, 0], dtype=np.float64)
        out.append(as_mcmc(y, start=xstart, end=xend, thin=xthin))

    if nchain == 1:
        return out[0]
    return as_mcmc_list(out)
