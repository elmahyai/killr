"""Number of chains in MCMC objects.

Translated from coda 0.19-4.1 ``nchain`` in ``R/mcextractor.R``.
"""

from __future__ import annotations

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import is_mcmc_list


def nchain(x):
    """Return the number of chains in an ``Mcmc`` (1) or ``McmcList`` object."""
    if is_mcmc(x):
        return 1
    if is_mcmc_list(x):
        return len(x)
    return None
