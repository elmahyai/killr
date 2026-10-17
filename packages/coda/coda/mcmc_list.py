"""Constructor for a list of MCMC objects.

Translated from coda 0.19-4.1 ``mcmc.list`` in ``R/mcmclist.R``.
"""

from __future__ import annotations

from coda.as_mcmc_list import McmcList, _mcmc_list


def mcmc_list(*args):
    """Build an ``McmcList`` from one or more ``Mcmc`` chains (``mcmc.list``)."""
    return _mcmc_list(*args)


__all__ = ["McmcList", "mcmc_list"]
