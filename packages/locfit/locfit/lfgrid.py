"""Evaluation-grid constructor from locfit."""

from __future__ import annotations

import numpy as np


def lfgrid(mg=10, ll=None, ur=None):
    if ll is None:
        ll = np.zeros(10)
    if ur is None:
        ur = np.zeros(10)
    mg_arr = np.asarray(mg, dtype=int).reshape(-1)
    if mg_arr.size == 1:
        mg_arr = np.repeat(mg_arr, 10)
    return {
        "type": "grid",
        "xev": 0,
        "mg": mg_arr,
        "cut": 0,
        "ll": np.asarray(ll, dtype=float),
        "ur": np.asarray(ur, dtype=float),
        "class": "lf_evs",
    }


__all__ = ["lfgrid"]
