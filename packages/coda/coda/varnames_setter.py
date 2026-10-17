"""Set variable names for MCMC objects.

Translated from coda 0.19-4.1 ``varnames<-`` in ``R/mcextractor.R``.
"""

from __future__ import annotations

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import is_mcmc_list


def set_varnames(x, value):
    """Set variable names for an ``Mcmc`` or ``McmcList``.
    
    Parameters
    ----------
    x : Mcmc or McmcList
        The MCMC object to modify
    value : list of str or None
        The new variable names
        
    Returns
    -------
    The modified object with new column names
    """
    if not is_mcmc(x) and not is_mcmc_list(x):
        return x
    
    if is_mcmc(x):
        # Set colnames attribute on the Mcmc object
        x.colnames = value
    else:
        # Set colnames on all chains in McmcList
        for chain in x.chains:
            chain.colnames = value
    
    return x
