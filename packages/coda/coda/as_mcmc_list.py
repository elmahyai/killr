"""Coerce objects to replicated MCMC lists.

Translated from coda 0.19-4.1 ``as.mcmc.list`` and ``as.mcmc.list.default``
(``mcmc.list`` validation lives in ``_mcmc_list``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from coda.as_mcmc import Mcmc, is_mcmc


@dataclass
class McmcList:
    """Parallel MCMC chains with matching iterations and variables."""

    chains: list[Mcmc]

    def __iter__(self):
        return iter(self.chains)

    def __len__(self):
        return len(self.chains)


def is_mcmc_list(x):
    """Return True when ``x`` is an ``McmcList`` (``is.mcmc.list``)."""
    return isinstance(x, McmcList)


def as_mcmc_list(x, **kwargs):
    """Coerce ``x`` to an ``McmcList`` (``as.mcmc.list.default``)."""
    if is_mcmc_list(x):
        return x
    return _mcmc_list(x)


def _mcmc_list(*args):
    """Build an ``McmcList`` from MCMC chains (``mcmc.list``)."""
    if len(args) == 0:
        raise TypeError("mcmc.list requires at least one argument")

    if len(args) == 1:
        value = args[0]
        if is_mcmc_list(value):
            return value
        if isinstance(value, (list, tuple)):
            chains = list(value)
            if len(chains) == 1 and isinstance(chains[0], (list, tuple)) and not is_mcmc(chains[0]):
                chains = list(chains[0])
        else:
            chains = [value]
    else:
        chains = list(args)

    if not all(is_mcmc(chain) for chain in chains):
        raise ValueError("Arguments must be mcmc objects")

    if len(chains) >= 2:
        ref_mcpar = np.asarray(chains[0].mcpar, dtype=np.float64)
        for chain in chains[1:]:
            if not np.array_equal(np.asarray(chain.mcpar, dtype=np.float64), ref_mcpar):
                raise ValueError("Different start, end or thin values in each chain")

        ref_nvar = _nvar_mcmc(chains[0])
        for chain in chains[1:]:
            if _nvar_mcmc(chain) != ref_nvar:
                raise ValueError("Different number of variables in each chain")

        ref_names = _varnames_mcmc(chains[0], allow_null=False)
        for chain in chains[1:]:
            if _varnames_mcmc(chain, allow_null=False) != ref_names:
                raise ValueError("Different variable names in each chain")

    return McmcList(chains=chains)


def _nvar_mcmc(chain):
    data = np.asarray(chain.data)
    if data.ndim >= 2:
        return int(data.shape[1])
    return 1


def _varnames_mcmc(chain, allow_null=True):
    names = getattr(chain, "colnames", None)
    if names is not None:
        return [str(name) for name in names]

    data = np.asarray(chain.data)
    if data.ndim >= 2 and data.dtype.names is not None:
        return list(data.dtype.names)

    if not allow_null:
        return [f"var{index}" for index in range(1, _nvar_mcmc(chain) + 1)]
    return None
