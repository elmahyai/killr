"""Random inverse Gaussian variates.

Translated from statmod 1.5.2 ``rinvgauss`` in ``R/invgauss.R``.
"""

from __future__ import annotations

import numpy as np

from boot.rng import unif
from extradistr._rng import norm_rand

from statmod.dinvgauss import _rep_len


def rinvgauss(n, mean=1, shape=None, dispersion=1):
    """Sample from the inverse Gaussian distribution."""
    if shape is not None:
        dispersion = 1.0 / np.asarray(shape, dtype=np.float64)

    n_arr = np.asarray(n)
    if n_arr.size > 1:
        count = int(n_arr.size)
    else:
        count = int(n)

    if count < 0:
        raise ValueError("n can't be negative")

    mean_arr = np.asarray(mean, dtype=np.float64)
    phi_arr = np.asarray(dispersion, dtype=np.float64)
    if count == 0 or mean_arr.size == 0 or phi_arr.size == 0:
        return np.array([], dtype=np.float64)

    mu = _rep_len(mean_arr, count)
    phi = _rep_len(phi_arr, count)

    r = np.zeros(count, dtype=np.float64)

    mu_ok = (mu > 0) & np.isfinite(mu)
    phi_ok = (phi > 0) & np.isfinite(phi)
    ok = mu_ok & phi_ok

    if not np.all(ok):
        bad = ~ok
        mu_bad = mu[bad]
        phi_bad = phi[bad]
        phi_ok_bad = phi_ok[bad]
        bad_idx = np.flatnonzero(bad)

        invchisq = (mu_bad == np.inf) & phi_ok_bad
        invchisq[np.isnan(invchisq)] = False
        j_local = np.ones(bad_idx.size, dtype=bool)

        if np.any(invchisq):
            m = int(np.sum(invchisq))
            z = np.array([norm_rand() for _ in range(m)], dtype=np.float64)
            r[bad_idx[invchisq]] = (z**-2) / phi_bad[invchisq]
            j_local[invchisq] = False

        infdisp = (phi_bad == np.inf) & j_local
        infdisp[np.isnan(infdisp)] = False
        if np.any(infdisp):
            r[bad_idx[infdisp]] = 0.0
            j_local[infdisp] = False

        r[bad_idx[j_local]] = np.nan

        n_valid = int(np.sum(ok))
        if n_valid == 0:
            return r
    else:
        n_valid = count

    mu_ok_vals = mu[ok]
    phi_ok_vals = phi[ok]

    y = np.array([norm_rand() for _ in range(n_valid)], dtype=np.float64) ** 2
    yphi = y * phi_ok_vals * mu_ok_vals

    bigphi = yphi > 5e5
    x1 = np.empty(n_valid, dtype=np.float64)
    if np.any(bigphi):
        x1[bigphi] = 1.0 / yphi[bigphi]
        not_big = ~bigphi
        if np.any(not_big):
            yp = yphi[not_big]
            x1[not_big] = 1.0 + yp / 2.0 * (1.0 - np.sqrt(1.0 + 4.0 / yp))
    else:
        x1 = 1.0 + yphi / 2.0 * (1.0 - np.sqrt(1.0 + 4.0 / yphi))

    firstroot = np.array([unif() < 1.0 / (1.0 + x) for x in x1], dtype=bool)
    xout = np.empty(n_valid, dtype=np.float64)
    xout[firstroot] = x1[firstroot]
    xout[~firstroot] = 1.0 / x1[~firstroot]
    r[ok] = mu_ok_vals * xout

    return r
