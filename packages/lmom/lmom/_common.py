"""Shared adapters for the loaded lmom Rust kernels."""

from __future__ import annotations

import math
import numpy as np

import lmom_kernel


def lmr(name: str, para, nmom: int) -> np.ndarray:
    values, ifail = getattr(lmom_kernel, name)(
        np.asarray(para, dtype=np.float64), int(nmom)
    )
    if ifail:
        raise ValueError(f"{name} failed with IFAIL={ifail}")
    return np.asarray(values, dtype=np.float64)


def sample_lmom(x, nmom=4, sort_data=True, ratios=None, trim=0):
    """Common adapter for lmom::samlmu and its pure-R variants."""
    values = np.asarray(x, dtype=np.float64).ravel()
    if np.any(~np.isfinite(values)):
        raise ValueError("x contains missing or non-finite values")
    if trim:
        raise NotImplementedError("trimmed sample L-moments are not in the loaded kernel")
    if ratios is None:
        ratios = bool(sort_data)
    return np.asarray(
        lmom_kernel.samlm(values, int(nmom), bool(sort_data), bool(ratios)),
        dtype=np.float64,
    )


def _quadrature(n=100):
    nodes, weights = np.polynomial.legendre.leggauss(n)
    return (nodes + 1.0) / 2.0, weights / 2.0


def _lmr_from_quantile(qfunc, order=4, n=100):
    """Compute population L-moments from a quantile function."""
    p, w = _quadrature(n)
    q = np.asarray(qfunc(p), dtype=np.float64)
    if q.ndim == 0:
        q = np.full_like(p, q)
    out = []
    for r in range(1, int(order) + 1):
        # shifted Legendre polynomial coefficient form:
        # P_{r-1}(2p-1) = sum_j (-1)^(r-1-j) C(r-1,j) C(r-1+j,j) p^j
        coeff = np.zeros(r)
        for j in range(r):
            coeff[j] = ((-1) ** (r - 1 - j)
                        * math.comb(r - 1, j)
                        * math.comb(r - 1 + j, j))
        out.append((w * q * np.polynomial.polynomial.polyval(p, coeff)).sum())
    return np.asarray(out)
