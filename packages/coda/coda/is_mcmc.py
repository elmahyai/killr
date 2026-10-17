"""Test for an MCMC chain object.

Translated from coda 0.19-4.1 ``is.mcmc`` in ``R/mcmc.R``.
"""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import Mcmc

_OBSOLETE = "Obsolete mcmc object\nUpdate with a command like\nx <- mcmcUpgrade(x)"


def is_mcmc(x):
    """Return whether ``x`` is an ``Mcmc`` chain.

    A three-dimensional chain is the pre-0.4 array layout and raises
    ``ValueError``, matching ``stop`` in R.
    """
    if isinstance(x, Mcmc):
        if np.asarray(x.data).ndim == 3:
            raise ValueError(_OBSOLETE)
        return True
    return False
