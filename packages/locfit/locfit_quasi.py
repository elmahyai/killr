"""locfit.quasi: R's quasi-likelihood weight iteration.

Weights are ``w0 / var(fitted)`` with ``var`` the function argument (``abs``
by default), so ``var(fh)`` in R is ``abs(fh)``. The fitted values come from
the crate's ``sfitted`` (on the fit, ``locfit_raw``).

The default ``ev = rbox()`` is the crate's adaptive tree (vertices fitted,
then interpolated at the data), so no ``ev`` argument is needed. An explicit
``ev`` in ``kwargs`` is passed through to ``locfit_raw``.
"""

from __future__ import annotations

import numpy as np

from .locfit_raw import fitted, locfit_raw


def locfit_quasi(x, y, weights=None, iter=3, var=np.abs, **kwargs):
    yv = np.asarray(y, dtype=float).reshape(-1)
    n = yv.size
    w0 = np.ones(n) if weights is None else np.resize(np.asarray(weights, dtype=float), n)
    lfq = w0
    fit = None
    for _ in range(int(iter) + 1):
        fit = locfit_raw(x, yv, weights=lfq, **kwargs)
        fh = fitted(fit)
        lfq = w0 / var(fh)
    fit["call"] = "locfit.quasi"
    return fit
