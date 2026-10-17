"""Number of variables in MCMC objects.

Translated from coda 0.19-4.1 ``nvar`` in ``R/mcextractor.R``.
"""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import is_mcmc_list


def nvar(x):
    """Return the number of variables in an ``Mcmc`` or ``McmcList`` object."""
    if is_mcmc(x):
        return _nvar_mcmc(x)
    if is_mcmc_list(x):
        return _nvar_mcmc(x.chains[0])
    return None


def _nvar_mcmc(chain):
    data = np.asarray(chain.data)
    if data.ndim >= 2:
        return int(data.shape[1])
    return 1
