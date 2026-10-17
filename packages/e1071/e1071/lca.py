"""Latent class analysis (e1071 ``lca``)."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from e1071.patterns import bincombinations, countpattern


def _boot_unif():
    try:
        from boot.rng import unif
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import unif
    return unif


def _is_data_matrix(x: Any) -> bool:
    if isinstance(x, np.ndarray):
        return x.ndim == 2
    if isinstance(x, (list, tuple)) and x:
        first = x[0]
        return isinstance(first, (list, tuple, np.ndarray))
    return False


def _max_col(matrix: np.ndarray) -> list[int]:
    """R ``max.col`` with ``ties.method = \"random\"``; 1-based column indices."""
    unif = _boot_unif()
    chosen: list[int] = []
    for row in np.asarray(matrix, dtype=float):
        which = 0
        ntie = 1
        best = float(row[0])
        for index in range(1, len(row)):
            value = float(row[index])
            if value > best:
                which = index
                ntie = 1
                best = value
            elif value == best:
                ntie += 1
                if ntie * unif() < 1.0:
                    which = index
        chosen.append(which + 1)
    return chosen


def lca(x, k, niter=100, matchdata=False, verbose=False):
    """Fit a latent class model with ``k`` classes."""
    unif = _boot_unif()
    xmat: list[int] | None = None
    if _is_data_matrix(x):
        if matchdata:
            counts, matched = countpattern(x, matching=True)
            xmat = matched
            x = counts
        else:
            x = countpattern(x, matching=False)
    else:
        matchdata = False

    counts = np.asarray(x, dtype=float)
    n = float(counts.sum())
    npat = counts.shape[0]
    nvar = int(round(math.log(npat) / math.log(2)))

    b = np.asarray(bincombinations(nvar), dtype=float)

    classprob = np.array([unif() for _ in range(int(k))], dtype=float)
    classprob = classprob / classprob.sum()
    draws = [unif() for _ in range(nvar * int(k))]
    p = np.array(draws, dtype=float).reshape(int(k), nvar, order="F")

    pas = np.zeros((int(k), npat), dtype=float)
    classsize = np.zeros(int(k), dtype=float)

    for iteration in range(int(niter)):
        for j in range(int(k)):
            mp = b * p[j, :] + (1.0 - b) * (1.0 - p[j, :])
            pas[j, :] = np.exp(np.log(mp).sum(axis=1))

        pas *= classprob[:, np.newaxis]

        sump = pas.sum(axis=0)
        pas /= sump[np.newaxis, :]

        spas = pas * counts[np.newaxis, :]
        classsize = spas.sum(axis=1)
        classprob = classsize / n

        xb = counts[:, np.newaxis] * b
        p = pas @ xb / classsize[:, np.newaxis]

        if verbose:
            print(f"Iteration: {iteration + 1} ")

    for j in range(int(k)):
        mp = b * p[j, :] + (1.0 - b) * (1.0 - p[j, :])
        pas[j, :] = np.exp(np.log(mp).sum(axis=1)) * classprob[j]

    pmust = pas.sum(axis=0)
    ll = float(np.sum(counts * np.log(pmust)))

    xg0 = counts[counts > 0]
    ll0 = float(np.sum(xg0 * np.log(xg0 / n)))
    lq = 2.0 * (ll0 - ll)

    bic = -2.0 * ll + math.log(n) * (int(k) * (nvar + 1) - 1)
    bicsat = -2.0 * ll0 + math.log(n) * (2**nvar - 1)

    ch = float(np.sum((counts - n * pmust) ** 2 / (n * pmust)))

    sump = pas.sum(axis=0)
    pas /= sump[np.newaxis, :]

    mat = _max_col(pas.T)
    if matchdata and xmat is not None:
        mat = [mat[int(idx) - 1] for idx in xmat]

    return {
        "classprob": classprob,
        "p": p,
        "matching": mat,
        "logl": ll,
        "loglsat": ll0,
        "chisq": ch,
        "lhquot": lq,
        "bic": bic,
        "bicsat": bicsat,
        "n": n,
        "np": int(k) * (nvar + 1) - 1,
        "matchdata": matchdata,
    }
