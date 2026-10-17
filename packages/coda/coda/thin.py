"""Thinning interval for MCMC objects.

Translated from coda 0.19-4.1 ``thin.mcmc`` and ``thin.mcmc.list`` in
``R/mcmc.R`` and ``R/mcmclist.R``.
"""

from __future__ import annotations

from coda.as_mcmc import as_mcmc, is_mcmc
from coda.as_mcmc_list import is_mcmc_list


def thin(x, **kwargs):
    """Return the thinning interval of an ``Mcmc`` or ``McmcList`` object."""
    if is_mcmc(x):
        return float(as_mcmc(x).thin)
    if is_mcmc_list(x):
        return thin(x.chains[0], **kwargs)
    return None
