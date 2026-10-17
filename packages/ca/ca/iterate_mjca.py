"""Iterative Burt-matrix update used by joint correspondence analysis."""

import numpy as np


def iterate_mjca(B, lev_n, nd=2, maxit=50, epsilon=1e-4):
    b = np.asarray(B, dtype=float)
    lev_n = np.asarray(lev_n, dtype=int)
    n = b.sum()
    groups = np.repeat(np.arange(len(lev_n)), lev_n)
    dummy = groups[:, None] == groups[None, :]
    def update(obj, adjusted=False):
        p = obj / n
        cm = p.sum(axis=0)
        ecm = np.outer(cm, cm)
        s = (p - ecm) / np.sqrt(ecm)
        vals, vecs = np.linalg.eigh(s)
        order = np.argsort(vals)[::-1]
        vals, vecs = vals[order], vecs[:, order]
        phi = vecs[:, :nd] / np.sqrt(cm)[:, None]
        lam = vals
        if adjusted:
            # R keeps the eigenvalues >= 1/Q first, then takes the first nd of them.
            q = len(lev_n)
            lam = (q / (q - 1)) ** 2 * (lam[lam >= 1 / q] - 1 / q) ** 2
        lam = np.concatenate([lam[:nd], np.full(max(0, nd - len(lam)), np.nan)])
        coord = np.zeros_like(ecm)
        for k in range(nd):
            coord = coord + lam[k] * np.outer(phi[:, k], phi[:, k])
        result = obj * (~dummy) + n * ecm * dummy * (1 + coord)
        return np.nan_to_num(result, nan=0.0, posinf=1e100, neginf=-1e100)

    current = update(b, adjusted=True)
    delta = np.inf
    k = 0
    while k < maxit and delta > epsilon:
        new = update(current)
        delta = np.max(np.abs(current - new))
        current = new
        k += 1
    return {"B.star": current, "crit": np.array([k, delta])}
