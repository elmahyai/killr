"""`da.mix` of mix 1.0-13 (R/mix.R): data augmentation from the posterior.

Each step draws the missing data (`istepm`, which uses the Park-Miller generator and
Box-Muller normals) and then draws the parameters from the complete-data posterior
(`pstepm`, which uses gamma and normal deviates). The generator must be seeded with
`rngseed` first.
"""

from __future__ import annotations

import numpy as np

from . import _kernel as K
from .em_mix import Theta, _prior_vector
from .na_codes import na_to_icode, na_to_snglcode
from .prelim_mix import MixData


def da_mix(s: MixData, start: Theta, steps: int = 1, prior=0.5,
           showits: bool = False) -> Theta:
    prior, w = _prior_vector(prior, s.ncells)
    z = na_to_snglcode(s.z, 999)
    wcodes = na_to_icode(s.w, 999)
    tp = np.zeros(s.p, dtype=np.int32)
    tq = np.zeros(s.q, dtype=np.int32)
    tmp = K.tobsm(s.q, s.psi, s.npsi, np.zeros(s.npsi), s.ncells,
                  np.zeros((s.q, s.ncells)), np.zeros(s.ncells), s.npattz, s.rz,
                  s.mdpzgrp, s.npattw, s.p, s.rw, s.mdpwgrp, s.ngrp, s.mobs,
                  s.mobsst, s.nmobs, s.n, z, tp, tq)
    kn1, kn2, kn3 = tmp["t1"], tmp["t2"], tmp["t3"]

    sigma = np.asarray(start.sigma, dtype=float)
    pii = np.asarray(start.pi, dtype=float)
    mu = np.asarray(start.mu, dtype=float)
    t1, t2, t3 = sigma.copy(), mu.copy(), pii.copy()
    if showits:
        print("Steps of Data Augmentation: ")
    for i in range(1, int(steps) + 1):
        if showits:
            print(f"{i}...", end="")
        tmp = K.istepm(s.q, s.psi, s.npsi, s.ncells, sigma, mu, pii, kn1, kn2, kn3,
                       t1, t2, t3, s.npattz, s.rz, tq, tq, s.mdpzgrp, s.npattw, s.p,
                       s.rw, tp, s.mdpwgrp, s.ngrp, s.mobs, s.mobsst, s.nmobs, s.n, z,
                       s.d, s.jmp, tp, kn3, kn1, wcodes, np.zeros(s.q))
        t1, t2, t3 = tmp["t1"], tmp["t2"], tmp["t3"]
        tmp = K.pstepm(s.q, s.psi, s.npsi, s.ncells, t1, t2, t3, s.n, s.p, prior,
                       np.zeros(s.npsi), np.zeros((s.q, s.q)), np.zeros(s.q), tq,
                       err=0.0)
        if tmp["err"] == 1:
            raise ValueError("Improper posterior--empty cells")
        sigma, mu, pii = tmp["sigma"], tmp["mu"], tmp["pi"]
    if showits:
        print()
    mu = mu.copy()
    mu[:, ~w] = np.nan
    return Theta(sigma=sigma, mu=mu, pi=pii)
