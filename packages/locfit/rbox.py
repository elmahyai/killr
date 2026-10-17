"""Evaluation-box constructor from locfit."""

import numpy as np


def rbox(cut=0.8, type="tree", ll=None, ur=None):
    """Construct an ``lf_evs``-compatible evaluation specification."""
    if type not in ("tree", "kdtree", "kdcenter", "phull"):
        raise ValueError("Invalid type argument")
    if ll is None:
        ll = np.zeros(10)
    if ur is None:
        ur = np.zeros(10)
    return {
        "type": type,
        "xev": 0,
        "mg": 0,
        "cut": float(cut),
        "ll": np.asarray(ll, dtype=float),
        "ur": np.asarray(ur, dtype=float),
    }
