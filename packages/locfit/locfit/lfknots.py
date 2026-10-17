"""Vertex table of a fit: translation of locfit 1.5-9.12 ``lfknots``.

The fit is any mapping (or object) with the R components ``nvc``, ``mi``,
``eva``, ``cell``, ``dp``, ``vnames`` and optionally ``trans``. ``coef`` is an
``nv x ncoef`` array in R column order (0-based here). Column names are not
returned; the column order follows ``what`` as in R.
"""

from __future__ import annotations

import numpy as np

from ._common import field

# locfit marks a missing fitted value with this constant before transforming.
MISSING_MARK = 0.1278433


def _identity(v):
    return v


def lfknots(x, tr=None, what=("x", "coef", "h", "nlx"), delete_pv=True):
    nv = int(field(field(x, "nvc"), "nv"))
    mi = field(x, "mi")
    d = int(field(mi, "d"))
    eva = field(x, "eva")
    coef = np.asarray(field(eva, "coef"), dtype=float).reshape(nv, -1)
    if tr is None:
        tr = field(x, "trans") or _identity

    cols = []
    for wh in what:
        if wh == "x":
            xev = np.asarray(field(eva, "xev"), dtype=float)
            cols.append(xev.reshape(nv, d))  # matrix(xev, ncol = d, byrow = TRUE)
        elif wh == "coef":
            mu = coef[:, 0].copy()
            mu[mu == MISSING_MARK] = np.nan
            cols.append(np.asarray(tr(mu), dtype=float).reshape(nv, 1))
        elif wh == "f1":
            cols.append(coef[:, 1:d + 1])
        elif wh == "nlx":
            cols.append(coef[:, d + 1:d + 2])
        elif wh == "nlx1":
            cols.append(coef[:, d + 2:2 * d + 2])
        elif wh == "se":
            rv = float(field(field(x, "dp"), "rv"))
            cols.append((np.sqrt(rv) * coef[:, d + 1]).reshape(nv, 1))
        elif wh == "infl":
            z = coef[:, 2 * d + 2]
            cols.append((z * z).reshape(nv, 1))
        elif wh == "infla":
            cols.append(coef[:, 2 * d + 3:3 * d + 3])
        elif wh == "lik":
            cols.append(coef[:, 3 * d + 3:3 * d + 6])
        elif wh == "h":
            cols.append(coef[:, 3 * d + 6:3 * d + 7])
        elif wh == "deg":
            cols.append(coef[:, 3 * d + 7:3 * d + 8])
        # Unknown names add nothing, as in the R loop.

    ret = np.column_stack(cols) if cols else np.empty((nv, 0))

    ev = int(field(mi, "ev"))
    if delete_pv and ev in (1, 2):
        s = np.asarray(field(field(x, "cell"), "s"))
        ret = ret[s == 0]  # R: ret[!as.logical(x$cell$s), ]
    return ret


__all__ = ["lfknots"]
