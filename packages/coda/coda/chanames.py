"""Chain names of MCMC list objects.

Translated from coda 0.19-4.1 ``chanames`` in ``R/mcextractor.R``.
"""

from __future__ import annotations

from coda.as_mcmc_list import is_mcmc_list


def chanames(x, allow_null=True):
    """Return chain names for an ``McmcList``, or ``None``."""
    if not is_mcmc_list(x):
        return None
    y = getattr(x, "chain_names", None)
    if y is None and not allow_null:
        y = [f"chain{index}" for index in range(1, len(x) + 1)]
    elif y is not None:
        y = [str(name) for name in y]
    return y
