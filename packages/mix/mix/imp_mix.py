"""`imp.mix` of mix 1.0-13 (R/mix.R): one imputation under a parameter value.

The missing categorical and continuous values are drawn by the Fortran `istepm`. The
continuous values are then put back on the original scale, and the rows are returned
to the original order.
"""

from __future__ import annotations

import numpy as np

from . import _kernel as K
from .em_mix import Theta
from .na_codes import na_to_icode, na_to_snglcode
from .prelim_mix import MixData


def imp_mix(s: MixData, theta: Theta, x=None) -> np.ndarray:
    sigma = np.asarray(theta.sigma, dtype=float)
    mu = np.asarray(theta.mu, dtype=float)
    pii = np.asarray(theta.pi, dtype=float)
    z = na_to_snglcode(s.z, 999)
    wcodes = na_to_icode(s.w, 999)
    tp = np.zeros(s.p, dtype=np.int32)
    tq = np.zeros(s.q, dtype=np.int32)
    tmp = K.istepm(s.q, s.psi, s.npsi, s.ncells, sigma, mu, pii, sigma, mu, pii,
                   sigma, mu, pii, s.npattz, s.rz, tq, tq, s.mdpzgrp, s.npattw, s.p,
                   s.rw, tp, s.mdpwgrp, s.ngrp, s.mobs, s.mobsst, s.nmobs, s.n, z,
                   s.d, s.jmp, tp, pii, sigma, wcodes, np.zeros(s.q))
    ro = s.ro - 1  # R's ro is 1-based
    w = tmp["w"][ro, :]
    # matrix(s$sdv, n, q, TRUE): each row is sdv, so column j is scaled by sdv[j]
    zz = tmp["z"] * s.sdv[np.newaxis, :] + s.xbar[np.newaxis, :]
    zz = zz[ro, :]
    if x is not None:
        zorig = np.asarray(x, dtype=float)[:, s.p:s.p + s.q]
        keep = ~np.isnan(zorig)
        zz[keep] = zorig[keep]
    return np.column_stack([w.astype(float), zz])
