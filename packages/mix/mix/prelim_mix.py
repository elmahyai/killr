"""`prelim.mix` of mix 1.0-13 (R/mix.R): preliminary manipulations of mixed data.

The categorical variables are in columns 1:p of x and are coded as positive integers.
The other columns are continuous. The rows are sorted by missingness pattern, the
observed cells are counted, and the continuous columns are centered and scaled by the
Fortran `ctrsc`. The result is the structure that em.mix, da.mix and imp.mix read.
Indices that R stores as 1-based stay 1-based, because the Fortran reads them so.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import _kernel as K
from .na_codes import code_to_na, na_to_icode, na_to_snglcode


@dataclass
class MixData:
    """The list that `prelim.mix` returns. Field names follow the R list."""

    w: np.ndarray        # n x p categorical codes, rows in sorted order (NaN = NA)
    n: int
    p: int
    d: np.ndarray        # number of categories of each categorical column
    jmp: np.ndarray      # cumd / d
    z: np.ndarray        # n x q centered and scaled continuous values (NaN = NA)
    q: int
    r: np.ndarray        # pattern display matrix
    rz: np.ndarray       # npattz x q, 1 = observed
    rw: np.ndarray       # npattw x p, 1 = observed
    nmis: np.ndarray
    ro: np.ndarray       # 1-based inverse row order, as R's `ro`
    mdpzgrp: np.ndarray
    mdpwgrp: np.ndarray
    mobs: np.ndarray     # 1-based cell number of each group
    mobsst: np.ndarray   # 1-based first row of each group
    nmobs: np.ndarray    # rows in each group
    ncells: int
    ngrp: int
    npattz: int
    npattw: int
    npsi: int
    psi: np.ndarray      # q x q packed-storage index, 1-based
    xbar: np.ndarray
    sdv: np.ndarray
    rnames: None = None
    wnames: None = None
    znames: None = None


def _duplicated(a: np.ndarray) -> np.ndarray:
    """R's `duplicated`: True after the first occurrence of each value."""
    seen: set = set()
    out = np.zeros(len(a), dtype=bool)
    for i, v in enumerate(a.tolist()):
        if v in seen:
            out[i] = True
        else:
            seen.add(v)
    return out


def prelim_mix(x, p) -> MixData:
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    n = x.shape[0]
    p = int(p)
    q = x.shape[1] - p
    if q < 1:
        raise ValueError("subscript out of bounds: no continuous columns")

    # w is stored as integer (truncated), z as double
    w = np.trunc(x[:, :p])
    z = x[:, p:p + q].copy()

    # missingness indicators; rz and rw are 1 when observed
    rz = np.isnan(z).astype(float)
    nmisz = rz.sum(axis=0).astype(int)
    mdpz = (rz @ (2.0 ** np.arange(q))).astype(int) + 1
    rz = 1.0 - rz
    rw = np.isnan(w).astype(float)
    nmisw = rw.sum(axis=0).astype(int)
    mdpw = (rw @ (2.0 ** np.arange(p))).astype(int) + 1
    rw = 1.0 - rw
    nmis = np.concatenate([nmisw, nmisz])

    # number of categories and the known part of the cell number
    d = np.empty(p, dtype=int)
    for j in range(p):
        obs = w[~np.isnan(w[:, j]), j]
        if obs.size == 0:
            raise ValueError("categorical column with no observed value")
        d[j] = int(obs.max())
    cumd = np.rint(np.exp(np.cumsum(np.log(d.astype(float))))).astype(int)
    mobs = 1.0 + ((na_to_icode(w, 1) - 1.0) * rw) @ (cumd / d)
    mobs = mobs.astype(int)

    # row sort by missingness pattern and cell
    ro = np.lexsort((mobs, mdpw, mdpz))
    w = w[ro]
    mdpw = mdpw[ro]
    mobs = mobs[ro]
    rw = rw[ro]
    z = z[ro]
    mdpz = mdpz[ro]
    rz = rz[ro]
    ro_inv = np.argsort(ro) + 1  # R: ro <- order(ro), 1-based

    # compress the z-patterns; mdpzst are 1-based first rows
    first = np.flatnonzero(np.r_[True, mdpz[1:] != mdpz[:-1]])
    mdpzst = first + 1
    mdpz_u = mdpz[first]
    npattz = len(mdpz_u)
    mdpzfin = np.r_[mdpzst[1:] - 1, n]
    mdpzgrp: list[int] = []
    mdpwst: list[int] = []
    mdpwtmp: list[int] = []
    for i in range(npattz):
        a, b = int(mdpzst[i]), int(mdpzfin[i])
        tmp = mdpw[a - 1:b]
        dup = _duplicated(tmp)
        mdpwst.extend((np.flatnonzero(~dup) + a).tolist())
        tmp_u = tmp[~dup]
        mdpzgrp.append(len(tmp_u))
        mdpwtmp.extend(tmp_u.tolist())
    mdpzgrp_a = np.array(mdpzgrp, dtype=int)
    mdpwst_a = np.array(mdpwst, dtype=int)
    mdpw = np.array(mdpwtmp, dtype=int)
    npattw = len(mdpw)

    # compress the w-patterns within each z-pattern; mobsst are 1-based first rows
    mdpwfin = np.r_[mdpwst_a[1:] - 1, n]
    mdpwgrp: list[int] = []
    mobsst: list[int] = []
    mobstmp: list[int] = []
    for i in range(npattw):
        a, b = int(mdpwst_a[i]), int(mdpwfin[i])
        tmp = mobs[a - 1:b]
        dup = _duplicated(tmp)
        mobsst.extend((np.flatnonzero(~dup) + a).tolist())
        tmp_u = tmp[~dup]
        mdpwgrp.append(len(tmp_u))
        mobstmp.extend(tmp_u.tolist())
    mobs = np.array(mobstmp, dtype=int)
    ngrp = len(mobs)
    mdpwgrp_a = np.array(mdpwgrp, dtype=int)
    mobsst_a = np.array(mobsst, dtype=int)

    # display matrix, one row per w-pattern
    r = np.hstack([rw, rz])[mdpwst_a - 1]

    ncells = int(cumd[p - 1])
    jmp = (cumd // d).astype(int)

    # pattern rows of rz and rw, first rows of each pattern
    rz = rz[mdpzst - 1].reshape(npattz, q)
    rw = rw[mdpwst_a - 1].reshape(npattw, p)

    npsi = q * (q + 1) // 2
    psi = K.mkpsi(q - 1)

    # center and scale the continuous columns, with NA coded as mvcode
    mvcode = float(np.nanmax(z)) + 1000.0
    zc = na_to_snglcode(z, mvcode)
    tmp = K.ctrsc(zc, n, q, mvcode)
    z = code_to_na(tmp["x"], mvcode)
    xbar = tmp["xbar"]
    sdv = tmp["sdv"]

    nmobs = np.r_[mobsst_a[1:], n + 1] - mobsst_a

    # The structure arrays are read-only in the Fortran, so they are kept as int32 in
    # Fortran order and passed to the kernel without a copy on each call.
    def i32(a):
        return np.asfortranarray(a, dtype=np.int32)

    return MixData(
        w=w, n=n, p=p, d=i32(d), jmp=i32(jmp), z=z, q=q, r=r, rz=i32(rz), rw=i32(rw),
        nmis=nmis, ro=ro_inv, mdpzgrp=i32(mdpzgrp_a), mdpwgrp=i32(mdpwgrp_a),
        mobs=i32(mobs), mobsst=i32(mobsst_a), nmobs=i32(nmobs), ncells=ncells,
        ngrp=ngrp, npattz=npattz, npattw=npattw, npsi=npsi, psi=psi, xbar=xbar,
        sdv=sdv,
    )
