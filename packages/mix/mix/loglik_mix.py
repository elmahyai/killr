"""`loglik.mix` of mix 1.0-13 (R/mix.R): observed-data log-likelihood of a parameter.

The sum over the missingness patterns and the observed cells is the Fortran kernel
`lobsm`, called with the same arguments as the R `.Fortran` call.
"""

from __future__ import annotations

import numpy as np

from . import _kernel as K
from .em_mix import Theta
from .na_codes import na_to_snglcode
from .prelim_mix import MixData


def loglik_mix(s: MixData, theta: Theta) -> float:
    z = na_to_snglcode(s.z, 999)
    tp = np.zeros(s.p, dtype=np.int32)
    tq = np.zeros(s.q, dtype=np.int32)
    return K.lobsm(s.q, s.psi, s.npsi, s.ncells, theta.sigma, theta.mu, theta.pi,
                   s.npattz, s.rz, tq, tq, s.mdpzgrp, s.npattw, s.p, s.rw, tp,
                   s.mdpwgrp, s.ngrp, s.mobs, s.mobsst, s.nmobs, s.n, z, s.d, s.jmp,
                   np.zeros(s.p, dtype=np.int32))
