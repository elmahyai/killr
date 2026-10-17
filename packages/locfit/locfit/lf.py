"""Construct a smooth GAM term, matching locfit's ``lf`` representation.

R's ``lf(...)`` returns ``cbind(...)`` with the attributes alpha, deg, scale,
kern, ev, maxk, call and class ``"smooth"``. The default ``ev = rbox()`` is the
adaptive kd-tree spec: type ``"tree"``, cut 0.8, ``ll`` and ``ur`` zero (R's
``rbox()`` defaults). The tree is built only when the term is fitted: a fit
with this ``ev`` goes to ``locfit_raw``, whose tree path is the crate kernel
(``crates/locfit``, ``fit_tree``). ``lf`` itself does no fitting.
"""

from __future__ import annotations

import numpy as np


def _default_ev():
    """R's default ``ev = rbox()``: a fresh dict per call (type tree, cut 0.8)."""
    return {
        "type": "tree",
        "xev": 0.0,
        "mg": 0.0,
        "cut": 0.8,
        "ll": np.zeros(10),
        "ur": np.zeros(10),
    }


def lf(*args, alpha=0.7, deg=2, scale=1, kern="tcub", ev=None, maxk=100):
    if not args:
        raise ValueError("at least one covariate is required")
    x = np.column_stack(args)
    return {
        "x": x,
        "alpha": alpha,
        "deg": deg,
        "scale": scale,
        "kern": kern,
        "ev": ev if ev is not None else _default_ev(),
        "maxk": maxk,
        "class": "smooth",
    }


__all__ = ["lf"]
