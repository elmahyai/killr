"""Binding of the mix Fortran kernels in crates/mix (mix_kernel).

Each wrapper takes the same arguments, in the same order, as the R `.Fortran` call in
mix 1.0-13 (R/mix.R) that it replaces, including the scratch arguments that R passes.
Every array is copied into a new Fortran-ordered array first, so the caller's arrays
are not changed, as R's `.Fortran` does not change them. Each wrapper returns a dict of
the arrays the Fortran sets, under the Fortran argument names, which is what R reads
from the returned list.

Shapes are checked here, because the Fortran does not check them.
"""

from __future__ import annotations

import numpy as np

import mix_kernel as _k

# `rngs` sets the Park-Miller seed. A routine that draws needs it first, because the
# Fortran stops on an unseeded generator, as R does.
_SEEDED = False


def _int(a, shape) -> np.ndarray:
    arr = np.array(a, dtype=np.int32, order="F", copy=True)
    if arr.shape != tuple(shape):
        raise ValueError(f"expected shape {tuple(shape)}, got {arr.shape}")
    return arr


def _dbl(a, shape) -> np.ndarray:
    arr = np.array(a, dtype=np.float64, order="F", copy=True)
    if arr.shape != tuple(shape):
        raise ValueError(f"expected shape {tuple(shape)}, got {arr.shape}")
    return arr


def _ro_int(a, shape) -> np.ndarray:
    """An int32 array the Fortran only reads: passed through when it already has the
    Fortran layout, so the structure of the data is not copied on every call."""
    if (isinstance(a, np.ndarray) and a.dtype == np.int32
            and a.shape == tuple(shape) and a.flags.f_contiguous):
        return a
    return _int(a, shape)


def _ro_dbl(a, shape) -> np.ndarray:
    """A float64 array the Fortran only reads; see `_ro_int`."""
    if (isinstance(a, np.ndarray) and a.dtype == np.float64
            and a.shape == tuple(shape) and a.flags.f_contiguous):
        return a
    return _dbl(a, shape)


def _need_seed() -> None:
    if not _SEEDED:
        raise RuntimeError("rngseed has not been called")


def rngs(seed) -> None:
    """`.Fortran("rngs", seed)`: sets the Park-Miller seed."""
    global _SEEDED
    _k.rngs(int(seed))
    _SEEDED = True


def mkpsi(p) -> np.ndarray:
    """`.Fortran("mkpsi", p, matrix(0, q, q))[[2]]`, with q = p + 1."""
    p = int(p)
    q = p + 1
    psi = _int(np.zeros((q, q)), (q, q))
    _k.mkpsi(p, psi)
    return psi


def ctrsc(x, n, p, mvcode) -> dict:
    """`.Fortran("ctrsc", x, n, p, xbar, sdv, mvcode)`."""
    n, p = int(n), int(p)
    x = _dbl(x, (n, p))
    xbar = _dbl(np.zeros(p), (p,))
    sdv = _dbl(np.zeros(p), (p,))
    _k.ctrsc(x, n, p, xbar, sdv, float(mvcode))
    return {"x": x, "xbar": xbar, "sdv": sdv}


def tobsm(q, psi, npsi, t1, ncells, t2, t3, npattz, rz, mdpzgrp, npattw, p, rw,
          mdpwgrp, ngrp, mobs, mobsst, nmobs, n, z, ocw, ocz) -> dict:
    """`.Fortran("tobsm", ...)`, 22 arguments. Sets t1, t2, t3."""
    q, npsi, ncells = int(q), int(npsi), int(ncells)
    npattz, npattw, p = int(npattz), int(npattw), int(p)
    ngrp, n = int(ngrp), int(n)
    t1 = _dbl(t1, (npsi,))
    t2 = _dbl(t2, (q, ncells))
    t3 = _dbl(t3, (ncells,))
    ocw = _int(ocw, (p,))
    ocz = _int(ocz, (q,))
    _k.tobsm(
        q, _ro_int(psi, (q, q)), npsi, t1, ncells, t2, t3,
        npattz, _ro_int(rz, (npattz, q)), _ro_int(mdpzgrp, (npattz,)),
        npattw, p, _ro_int(rw, (npattw, p)), _ro_int(mdpwgrp, (npattw,)),
        ngrp, _ro_int(mobs, (ngrp,)), _ro_int(mobsst, (ngrp,)), _ro_int(nmobs, (ngrp,)),
        n, _ro_dbl(z, (n, q)), ocw, ocz,
    )
    return {"t1": t1, "t2": t2, "t3": t3}


def stvlm(q, psi, npsi, t1, ncells, t2) -> dict:
    """`.Fortran("stvlm", q, psi, npsi, t1, ncells, t2)`: sigma = I, mu = 0."""
    q, npsi, ncells = int(q), int(npsi), int(ncells)
    t1 = _dbl(t1, (npsi,))
    t2 = _dbl(t2, (q, ncells))
    _k.stvlm(q, _ro_int(psi, (q, q)), npsi, t1, ncells, t2)
    return {"t1": t1, "t2": t2}


def estepm(q, psi, npsi, ncells, sigma, mu, pii, kn1, kn2, kn3, t1, t2, t3, npattz,
           rz, mcz, ocz, mdpzgrp, npattw, p, rw, mcw, mdpwgrp, ngrp, mobs, mobsst,
           nmobs, n, z, d, jmp, c, theta) -> dict:
    """`.Fortran("estepm", ...)`, 33 arguments. Sets t1, t2, t3."""
    q, npsi, ncells = int(q), int(npsi), int(ncells)
    npattz, npattw, p = int(npattz), int(npattw), int(p)
    ngrp, n = int(ngrp), int(n)
    t1 = _dbl(t1, (npsi,))
    t2 = _dbl(t2, (q, ncells))
    t3 = _dbl(t3, (ncells,))
    _k.estepm(
        q, _ro_int(psi, (q, q)), npsi, ncells,
        _dbl(sigma, (npsi,)), _dbl(mu, (q, ncells)), _dbl(pii, (ncells,)),
        _ro_dbl(kn1, (npsi,)), _ro_dbl(kn2, (q, ncells)), _ro_dbl(kn3, (ncells,)),
        t1, t2, t3,
        npattz, _ro_int(rz, (npattz, q)), _int(mcz, (q,)), _int(ocz, (q,)),
        _ro_int(mdpzgrp, (npattz,)),
        npattw, p, _ro_int(rw, (npattw, p)), _int(mcw, (p,)), _ro_int(mdpwgrp, (npattw,)),
        ngrp, _ro_int(mobs, (ngrp,)), _ro_int(mobsst, (ngrp,)), _ro_int(nmobs, (ngrp,)),
        n, _dbl(z, (n, q)), _ro_int(d, (p,)), _ro_int(jmp, (p,)), _int(c, (p,)),
        _dbl(theta, (ncells,)),
    )
    return {"t1": t1, "t2": t2, "t3": t3}


def mstepm(q, psi, npsi, ncells, t1, t2, t3, n, prior) -> dict:
    """`.Fortran("mstepm", ...)`: converts t1, t2, t3 to ML estimates."""
    q, npsi, ncells, n = int(q), int(npsi), int(ncells), int(n)
    t1 = _dbl(t1, (npsi,))
    t2 = _dbl(t2, (q, ncells))
    t3 = _dbl(t3, (ncells,))
    _k.mstepm(q, _ro_int(psi, (q, q)), npsi, ncells, t1, t2, t3, n,
              _ro_dbl(prior, (ncells,)))
    return {"t1": t1, "t2": t2, "t3": t3}


def istepm(q, psi, npsi, ncells, sigma, mu, pii, kn1, kn2, kn3, t1, t2, t3, npattz,
           rz, mcz, ocz, mdpzgrp, npattw, p, rw, mcw, mdpwgrp, ngrp, mobs, mobsst,
           nmobs, n, z, d, jmp, c, theta, chf, w, zz) -> dict:
    """`.Fortran("istepm", ...)`, 36 arguments. Sets t1, t2, t3, z and w."""
    _need_seed()
    q, npsi, ncells = int(q), int(npsi), int(ncells)
    npattz, npattw, p = int(npattz), int(npattw), int(p)
    ngrp, n = int(ngrp), int(n)
    t1 = _dbl(t1, (npsi,))
    t2 = _dbl(t2, (q, ncells))
    t3 = _dbl(t3, (ncells,))
    z = _dbl(z, (n, q))
    w = _int(w, (n, p))
    _k.istepm(
        q, _ro_int(psi, (q, q)), npsi, ncells,
        _dbl(sigma, (npsi,)), _dbl(mu, (q, ncells)), _dbl(pii, (ncells,)),
        _ro_dbl(kn1, (npsi,)), _ro_dbl(kn2, (q, ncells)), _ro_dbl(kn3, (ncells,)),
        t1, t2, t3,
        npattz, _ro_int(rz, (npattz, q)), _int(mcz, (q,)), _int(ocz, (q,)),
        _ro_int(mdpzgrp, (npattz,)),
        npattw, p, _ro_int(rw, (npattw, p)), _int(mcw, (p,)), _ro_int(mdpwgrp, (npattw,)),
        ngrp, _ro_int(mobs, (ngrp,)), _ro_int(mobsst, (ngrp,)), _ro_int(nmobs, (ngrp,)),
        n, z, _ro_int(d, (p,)), _ro_int(jmp, (p,)), _int(c, (p,)),
        _dbl(theta, (ncells,)), _dbl(chf, (npsi,)), w, _dbl(zz, (q,)),
    )
    return {"t1": t1, "t2": t2, "t3": t3, "z": z, "w": w}


def pstepm(q, psi, npsi, ncells, t1, t2, t3, n, p, prior, chf, mx, zz, mcz,
           err=0.0) -> dict:
    """`.Fortran("pstepm", ...)`, 15 arguments. Sets sigma, mu, pi and err."""
    _need_seed()
    q, npsi, ncells = int(q), int(npsi), int(ncells)
    n, p = int(n), int(p)
    t1 = _dbl(t1, (npsi,))
    t2 = _dbl(t2, (q, ncells))
    t3 = _dbl(t3, (ncells,))
    err_arr = _dbl([err], (1,))
    _k.pstepm(
        q, _ro_int(psi, (q, q)), npsi, ncells, t1, t2, t3, n, p,
        _ro_dbl(prior, (ncells,)), _dbl(chf, (npsi,)), _dbl(mx, (q, q)),
        _dbl(zz, (q,)), _int(mcz, (q,)), err_arr,
    )
    return {"sigma": t1, "mu": t2, "pi": t3, "err": float(err_arr[0])}


def lobsm(q, psi, npsi, ncells, sigma, mu, pii, npattz, rz, mcz, ocz, mdpzgrp,
          npattw, p, rw, mcw, mdpwgrp, ngrp, mobs, mobsst, nmobs, n, z, d, jmp,
          c) -> float:
    """`.Fortran("lobsm", ...)`, 27 arguments. Returns `ll`, the observed-data
    log-likelihood at (sigma, mu, pii)."""
    q, npsi, ncells = int(q), int(npsi), int(ncells)
    npattz, npattw, p = int(npattz), int(npattw), int(p)
    ngrp, n = int(ngrp), int(n)
    return float(_k.lobsm(
        q, _ro_int(psi, (q, q)), npsi, ncells,
        _dbl(sigma, (npsi,)), _dbl(mu, (q, ncells)), _dbl(pii, (ncells,)),
        npattz, _ro_int(rz, (npattz, q)), _int(mcz, (q,)), _int(ocz, (q,)),
        _ro_int(mdpzgrp, (npattz,)), npattw, p, _ro_int(rw, (npattw, p)),
        _int(mcw, (p,)), _ro_int(mdpwgrp, (npattw,)), ngrp,
        _ro_int(mobs, (ngrp,)), _ro_int(mobsst, (ngrp,)), _ro_int(nmobs, (ngrp,)),
        n, _ro_dbl(z, (n, q)), _ro_int(d, (p,)), _ro_int(jmp, (p,)), _int(c, (p,)),
    ))


def mstepcm(q, psi, npsi, ncells, t1, t2, t3, n, design) -> dict:
    """`.Fortran("mstepcm", ...)`, 19 arguments: the ECM M-step under the regression
    `design`. The scratch arrays of R's call are made here. Returns sigma and mu."""
    q, npsi, ncells, n = int(q), int(npsi), int(ncells), int(n)
    design = np.asarray(design, dtype=float)
    r = int(design.shape[1])
    npsir = r * (r + 1) // 2
    psir = mkpsi(r - 1)
    t1 = _dbl(t1, (npsi,))
    t2 = _dbl(t2, (q, ncells))
    t3 = _dbl(t3, (ncells,))
    sigma = _dbl(np.zeros(npsi), (npsi,))
    mu = _dbl(np.zeros((q, ncells)), (q, ncells))
    _k.mstepcm(
        q, _ro_int(psi, (q, q)), npsi, ncells, t1, t2, t3, sigma, mu, n, r,
        _dbl(design, (ncells, r)), _dbl(np.zeros(npsir), (npsir,)),
        _int(np.zeros(r), (r,)), psir, npsir, _dbl(np.zeros(r), (r,)),
        _dbl(np.zeros(ncells), (ncells,)), _dbl(np.zeros((r, q)), (r, q)),
    )
    return {"sigma": sigma, "mu": mu}


def ipf(ncells, table, fit, margins, p, d, jmp, eps) -> np.ndarray:
    """`.Fortran("ipf", ncells, table, fit, length(margins), margins, p, d, jmp, ...)`.
    One cycle of iterative proportional fitting. Returns the fitted `fit`, which R
    reads as element [[3]]."""
    ncells, p = int(ncells), int(p)
    margins = np.asarray(margins, dtype=np.int32).ravel()
    ncon = int(margins.size)
    table = _dbl(table, (ncells,))
    fit = _dbl(fit, (ncells,))
    _k.ipf(
        ncells, table, fit, ncon, _int(margins, (ncon,)), p,
        _ro_int(d, (p,)), _ro_int(jmp, (p,)), _int(np.zeros(p), (p,)),
        _int(np.zeros(p), (p,)), _int(np.zeros(p), (p,)), float(eps),
    )
    return fit


def pstepcm(q, psi, npsi, ncells, t1, t2, t3, n, design) -> dict:
    """`.Fortran("pstepcm", ...)`, 22 arguments: the complete-data posterior under the
    regression `design`. Draws with the Park-Miller generator, so `rngseed` must come
    first. Returns sigma and mu. The t1 array is copied, as R's call does not change it."""
    _need_seed()
    q, npsi, ncells, n = int(q), int(npsi), int(ncells), int(n)
    design = np.asarray(design, dtype=float)
    r = int(design.shape[1])
    npsir = r * (r + 1) // 2
    psir = mkpsi(r - 1)
    t1 = _dbl(t1, (npsi,))
    t2 = _dbl(t2, (q, ncells))
    t3 = _dbl(t3, (ncells,))
    sigma = _dbl(np.zeros(npsi), (npsi,))
    mu = _dbl(np.zeros((q, ncells)), (q, ncells))
    _k.pstepcm(
        q, _ro_int(psi, (q, q)), npsi, ncells, t1, t2, t3, sigma, mu, n, r,
        _dbl(design, (ncells, r)), _dbl(np.zeros(npsir), (npsir,)),
        _int(np.zeros(r), (r,)), psir, npsir, _dbl(np.zeros(r), (r,)),
        _dbl(np.zeros(ncells), (ncells,)), _int(np.zeros(q), (q,)),
        _dbl(np.zeros(npsi), (npsi,)), _dbl(np.zeros((r, q)), (r, q)),
        _dbl(np.zeros((q, q)), (q, q)),
    )
    return {"sigma": sigma, "mu": mu}


def bipf(ncells, table, theta, prior, margins, p, d, jmp) -> dict:
    """`.Fortran("bipf", ncells, table, theta, prior, length(margins), margins, p, d,
    jmp, ...)`. One cycle of Bayesian IPF. Draws gamma deviates, so `rngseed` must come
    first. Returns the updated `theta` (R's `pii`) and `err` (1 means improper)."""
    _need_seed()
    ncells, p = int(ncells), int(p)
    margins = np.asarray(margins, dtype=np.int32).ravel()
    ncon = int(margins.size)
    table = _dbl(table, (ncells,))
    theta = _dbl(theta, (ncells,))
    prior = _dbl(prior, (ncells,))
    err = _int([0], (1,))
    _k.bipf(
        ncells, table, theta, prior, ncon, _int(margins, (ncon,)), p,
        _ro_int(d, (p,)), _ro_int(jmp, (p,)), _int(np.zeros(p), (p,)),
        _int(np.zeros(p), (p,)), _int(np.zeros(p), (p,)), err,
    )
    return {"theta": theta, "err": int(err[0])}
