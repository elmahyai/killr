"""Evaluation-box specification: translation of locfit 1.5-9.12 ``rbox``."""

from __future__ import annotations

import numpy as np

from ._common import LfEvs

_TYPES = ("tree", "kdtree", "kdcenter", "phull")


def rbox(cut=0.8, type="tree", ll=None, ur=None):
    """Return an ``lf_evs`` record with the fields of the R list.

    R default for ``ll`` and ``ur`` is ``rep(0, 10)``.
    """
    if type not in _TYPES:
        raise ValueError("Invalid type argument")
    ll = np.zeros(10) if ll is None else np.asarray(ll, dtype=float).reshape(-1)
    ur = np.zeros(10) if ur is None else np.asarray(ur, dtype=float).reshape(-1)
    return LfEvs(type=type, xev=0.0, mg=0.0, cut=float(cut), ll=ll, ur=ur)


__all__ = ["rbox"]
