"""locfit.censor: R's censored Gaussian local regression (iterated pseudo-responses).

The loop is R's: refit with the current pseudo-response, take fitted values,
update sigma and the Mills-ratio step for the censored points, keep y where
not censored. The fitted values come from the crate's ``sfitted`` (on the
fit, ``locfit_raw``). The km = TRUE branch needs km.mrl, which is not wired
into this batch.

The default ``ev = rbox()`` is the crate's adaptive tree (vertices fitted,
then interpolated at the data), so no ``ev`` argument is needed. An explicit
``ev`` in ``kwargs`` is passed through to ``locfit_raw``.
"""

from __future__ import annotations

import math

import numpy as np

from .locfit_raw import fitted, locfit_raw

_erfc = np.vectorize(math.erfc, otypes=[float])


def _dnorm(z):
    return np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _pnorm(q):
    return 0.5 * _erfc(-np.asarray(q, dtype=float) / math.sqrt(2.0))


def locfit_censor(x, y, cens, iter=3, km=False, **kwargs):
    if km:
        raise NotImplementedError("km = TRUE needs km.mrl wired into this batch; not verified")
    yv = np.asarray(y, dtype=float).reshape(-1)
    c = np.asarray(cens) != 0
    lfc_y = yv.copy()
    fit = None
    for _ in range(int(iter) + 1):
        fit = locfit_raw(x, lfc_y, **kwargs)
        fh = fitted(fit)
        rdf = np.sum(1 - c) - 2 * fit["dp"]["df1"] + fit["dp"]["df2"]
        sigma = np.sqrt(np.sum((yv - fh) * (lfc_y - fh)) / rdf)
        sr = (yv - fh) / sigma
        lfc_y = fh + sigma * _dnorm(sr) / _pnorm(-sr)
        lfc_y[~c] = yv[~c]
    fit["call"] = "locfit.censor"
    return fit
