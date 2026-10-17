"""Parametric bootstrap for latent class analysis (e1071 ``bootstrap.lca``)."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from e1071.lca import lca
from e1071.patterns import countpattern


def _boot_rng():
    try:
        from boot.censored import _weighted_index
        from boot.rng import unif
    except ImportError:
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "boot"))
        from boot.censored import _weighted_index
        from boot.rng import unif
    return unif, _weighted_index


def _pnorm(x: float) -> float:
    return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))


def _r_sd(values: list[float] | np.ndarray) -> float:
    arr = np.asarray(values, dtype=float)
    if np.any(np.isnan(arr)):
        return float("nan")
    n = arr.size
    if n < 2:
        return float("nan")
    mean = float(arr.mean())
    return float(math.sqrt(np.sum((arr - mean) ** 2) / (n - 1)))


def _r_prop_less(reference: float, values: list[float] | np.ndarray) -> float:
    """``sum(reference < values) / length(values)`` with R ``NA`` propagation."""
    if any(math.isnan(float(v)) for v in values):
        return float("nan")
    return sum(reference < float(v) for v in values) / len(values)


def bootstrap_lca(l: dict[str, Any], nsamples: int = 10, lcaiter: int = 30, verbose: bool = False):
    """Parametric bootstrap for a fitted ``lca`` model."""
    unif, weighted_index = _boot_rng()

    n = float(l["n"])
    classprob = np.asarray(l["classprob"], dtype=float).reshape(-1)
    nclass = classprob.size
    prob = np.asarray(l["p"], dtype=float)
    nvar = prob.shape[1]

    ll: list[float] = []
    ll0: list[float] = []
    lq: list[float] = []
    ch: list[float] = []

    n_obs = int(n)
    classprob_list = [float(v) for v in classprob]

    for i in range(int(nsamples)):
        cm = weighted_index(nclass, n_obs, classprob_list)
        cm0 = np.asarray(cm, dtype=int) - 1
        prob_rows = prob[cm0, :]

        draws = [unif() for _ in range(n_obs * nvar)]
        xmat = np.asarray(draws, dtype=float).reshape(n_obs, nvar, order="F")
        xmat = (xmat < prob_rows).astype(float)
        x = countpattern(xmat, matching=False)

        if verbose:
            print(f"Start of Bootstrap Sample {i + 1} ")

        lc = lca(x, nclass, niter=lcaiter, verbose=verbose)

        ll.append(float(lc["logl"]))
        ll0.append(float(lc["loglsat"]))
        lq.append(float(lc["lhquot"]))
        ch.append(float(lc["chisq"]))

        if verbose:
            print(
                f"LL: {ll[-1]}  LLsat: {ll0[-1]} "
                f"Ratio: {lq[-1]}  Chisq: {ch[-1]} "
            )

    lratm = float(np.mean(lq)) if lq else float("nan")
    lrats = _r_sd(lq)
    chisqm = float(np.mean(ch)) if ch else float("nan")
    chisqs = _r_sd(ch)

    lhquot_org = float(l["lhquot"])
    chisq_org = float(l["chisq"])

    zl = (lhquot_org - lratm) / lrats
    zc = (chisq_org - chisqm) / chisqs
    pzl = 1.0 - _pnorm(zl)
    pzc = 1.0 - _pnorm(zc)
    pl = _r_prop_less(lhquot_org, lq)
    pc = _r_prop_less(chisq_org, ch)

    return {
        "logl": np.asarray(ll, dtype=float),
        "loglsat": np.asarray(ll0, dtype=float),
        "lratio": np.asarray(lq, dtype=float),
        "lratiomean": lratm,
        "lratiosd": lrats,
        "lratioorg": lhquot_org,
        "zratio": zl,
        "pvalzratio": pzl,
        "pvalratio": pl,
        "chisq": np.asarray(ch, dtype=float),
        "chisqmean": chisqm,
        "chisqsd": chisqs,
        "chisqorg": chisq_org,
        "zchisq": zc,
        "pvalzchisq": pzc,
        "pvalchisq": pc,
        "nsamples": int(nsamples),
        "lcaiter": int(lcaiter),
    }
