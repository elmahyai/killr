"""Test for an MCMC chain list.

Translated from coda 0.19-4.1 ``is.mcmc.list`` in ``R/mcmclist.R``.
"""

from __future__ import annotations

from coda.as_mcmc_list import McmcList


def is_mcmc_list(x):
    """Return True when ``x`` inherits the MCMC list class."""
    return isinstance(x, McmcList)
