"""locfit.robust: R's bisquare-reweighted local regression.

R ignores the ``weights`` argument: the first pass uses unit weights, then
each pass uses ``max(1 - (res / (6 s))^2, 0)^2`` with ``s = median(|res|)``
and ``res = y - fitted`` the raw residuals. The fitted values come from the
crate's ``sfitted`` (on the fit, ``locfit_raw``).

The default ``ev = rbox()`` is the crate's adaptive tree (vertices fitted,
then interpolated at the data), so no ``ev`` argument is needed. An explicit
``ev`` in ``kwargs`` is passed through to ``locfit_raw``.
"""

from __future__ import annotations

import numpy as np

from .locfit_raw import locfit_raw, residuals


def locfit_robust(x, y, weights=None, iter=3, **kwargs):
    yv = np.asarray(y, dtype=float).reshape(-1)
    lfr = np.ones(yv.size)
    fit = None
    for _ in range(int(iter) + 1):
        fit = locfit_raw(x, yv, weights=lfr, **kwargs)
        res = residuals(fit)
        s = np.median(np.abs(res))
        lfr = np.maximum(1.0 - (res / (6.0 * s)) ** 2, 0.0) ** 2
    fit["call"] = "locfit.robust"
    return fit
