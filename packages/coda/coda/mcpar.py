"""Extract MCMC simulation parameters."""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import is_mcmc


def mcpar(x):
    """Return the start, end, and thinning interval for an MCMC object."""
    if is_mcmc(x):
        return np.asarray(x.mcpar, dtype=np.float64).copy()
    raise TypeError("no mcpar method for this object")
