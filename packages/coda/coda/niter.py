"""Number of iterations in MCMC objects.

Translated from coda 0.19-4.1 ``niter`` in ``R/mcextractor.R``.
"""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import is_mcmc_list


def niter(x):
    """Return the number of iterations in an ``Mcmc`` or ``McmcList`` object."""
    if is_mcmc(x):
        return _niter_mcmc(x)
    if is_mcmc_list(x):
        return _niter_mcmc(x.chains[0])
    return None


def _niter_mcmc(chain):
    data = np.asarray(chain.data)
    if data.ndim >= 2:
        return int(data.shape[0])
    return int(data.size)
