"""`em.mix` of mix 1.0-13 (R/mix.R): maximum likelihood by EM for the mixed model.

The E-step and M-step are the Fortran kernels `estepm` and `mstepm`, called with the
same arguments as the R code. The start is the Fortran `stvlm` unless one is given.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

from . import _kernel as K
from .na_codes import na_to_snglcode
from .prelim_mix import MixData


@dataclass
class Theta:
    """The list of parameters that em.mix, da.mix and imp.mix return and take."""

    sigma: np.ndarray
    mu: np.ndarray
    pi: np.ndarray


def _prior_vector(prior, ncells: int):
    """`if(length(prior)==1) prior <- rep(prior, ncells)`; structural zeros are -999."""
    prior = np.asarray(prior, dtype=float)
    if prior.size == 1:
        prior = np.repeat(prior.ravel(), ncells)
    w = ~np.isnan(prior)
    prior = prior.copy()
    prior[~w] = -999.0
    return prior, w


def em_mix(s: MixData, start: Theta | None = None, prior=1.0, maxits: int = 1000,
           showits: bool = True, eps: float = 0.0001) -> Theta:
    prior, w = _prior_vector(prior, s.ncells)
    z = na_to_snglcode(s.z, 999)
    tp = np.zeros(s.p, dtype=np.int32)
    tq = np.zeros(s.q, dtype=np.int32)
    sigma = np.zeros(s.npsi)
    pii = np.zeros(s.ncells)
    mu = np.zeros((s.q, s.ncells))
    tmp = K.tobsm(s.q, s.psi, s.npsi, sigma, s.ncells, mu, pii, s.npattz, s.rz,
                  s.mdpzgrp, s.npattw, s.p, s.rw, s.mdpwgrp, s.ngrp, s.mobs,
                  s.mobsst, s.nmobs, s.n, z, tp, tq)
    kn1, kn2, kn3 = tmp["t1"], tmp["t2"], tmp["t3"]

    if start is None:
        tmp = K.stvlm(s.q, s.psi, s.npsi, sigma, s.ncells, mu)
        sigma, mu = tmp["t1"], tmp["t2"]
        pii = np.ones(s.ncells)
        pii[~w] = 0.0
    else:
        sigma = np.asarray(start.sigma, dtype=float)
        mu = np.asarray(start.mu, dtype=float)
        pii = np.asarray(start.pi, dtype=float)
        if np.any(pii[w] == 0):
            warnings.warn("Starting value on the boundary")
        if np.any(~w) and np.any(pii[~w] != 0):
            raise ValueError("starting value has nonzero elements for structural zeros")

    converged = False
    it = 0
    if showits:
        print("Steps of EM: ")
    t1, t2, t3 = sigma.copy(), mu.copy(), pii.copy()
    while (not converged) and it < maxits:
        it += 1
        if showits:
            print(f"{it}...", end="")
        if it > 1:
            sigma, mu, pii = t1.copy(), t2.copy(), t3.copy()
        tmp = K.estepm(s.q, s.psi, s.npsi, s.ncells, sigma, mu, pii, kn1, kn2, kn3,
                       t1, t2, t3, s.npattz, s.rz, tq, tq, s.mdpzgrp, s.npattw, s.p,
                       s.rw, tp, s.mdpwgrp, s.ngrp, s.mobs, s.mobsst, s.nmobs, s.n, z,
                       s.d, s.jmp, tp, kn3)
        t1, t2, t3 = tmp["t1"], tmp["t2"], tmp["t3"]
        tmp = K.mstepm(s.q, s.psi, s.npsi, s.ncells, t1, t2, t3, s.n, prior)
        t1, t2, t3 = tmp["t1"], tmp["t2"], tmp["t3"]
        if np.any(t3 < 0):
            raise ValueError("Estimate outside the parameter space. Check prior.")
        # t3[w][t3[w] < 1e-7/sum(w)] <- 0
        thr = 0.0000001 / int(w.sum())
        t3 = t3.copy()
        t3[w & (t3 < thr)] = 0.0
        c3 = bool(np.all(np.abs(t3 - pii) <= eps * np.abs(pii)))
        c2 = bool(np.all(np.abs(t2 - mu) <= eps * np.abs(mu)))
        c1 = bool(np.all(np.abs(t1 - sigma) <= eps * np.abs(sigma)))
        converged = c3 and c2 and c1
    if showits:
        print()
    return Theta(sigma=t1, mu=t2, pi=t3)
