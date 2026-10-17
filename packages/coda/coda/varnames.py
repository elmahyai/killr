"""Variable names of MCMC objects.

Translated from coda 0.19-4.1 ``varnames`` in ``R/mcextractor.R``.
"""

from __future__ import annotations

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import _nvar_mcmc, is_mcmc_list


def varnames(x, allow_null=True):
    """Return variable names for an ``Mcmc`` or ``McmcList``, or ``None``."""
    if not is_mcmc(x) and not is_mcmc_list(x):
        return None
    if is_mcmc(x):
        chain = x
    else:
        chain = x.chains[0]
    y = _chain_varnames(chain)
    if y is None and not allow_null:
        y = [f"var{index}" for index in range(1, _nvar_mcmc(chain) + 1)]
    return y


def _chain_varnames(chain):
    names = getattr(chain, "colnames", None)
    if names is None:
        return None
    return [str(name) for name in names]
