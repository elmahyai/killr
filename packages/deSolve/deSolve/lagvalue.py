"""Lagged state values for delay differential equations (deSolve ``lagvalue``)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_MISSING = object()


def _lag_kernel():
    try:
        from lagvalue import (
            init_hist as _init_hist,
            lagvalue_kernel,
            restore_hist as _restore_hist,
            update_hist as _update_hist,
            update_hist_ini as _update_hist_ini,
        )
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "lagvalue"))
        from lagvalue import (
            init_hist as _init_hist,
            lagvalue_kernel,
            restore_hist as _restore_hist,
            update_hist as _update_hist,
            update_hist_ini as _update_hist_ini,
        )
    return _init_hist, _update_hist, _update_hist_ini, _restore_hist, lagvalue_kernel


def init_hist(max: int, n_eq: int) -> None:
    """Initialise Hermite history buffers (``inithist`` with method 1)."""
    _init_hist, _, _, _, _ = _lag_kernel()
    _init_hist(int(max), int(n_eq))


def update_hist(t: float, y, dy) -> None:
    """Append one accepted step to the history ring (``updatehist``)."""
    _, _update_hist, _, _, _ = _lag_kernel()
    y_arr = np.asarray(y, dtype=float).reshape(-1)
    dy_arr = np.asarray(dy, dtype=float).reshape(-1)
    _update_hist(float(t), y_arr, dy_arr)


def update_hist_ini(t: float, y, dy) -> None:
    """First history entry at integration start (``updatehistini``)."""
    _, _, _update_hist_ini, _, _ = _lag_kernel()
    y_arr = np.asarray(y, dtype=float).reshape(-1)
    dy_arr = np.asarray(dy, dtype=float).reshape(-1)
    _update_hist_ini(float(t), y_arr, dy_arr)


def restore_hist(snapshot: dict) -> None:
    """Restore history from an R ``dump_lag_history`` snapshot (proof helper)."""
    _, _, _, _restore_hist, _ = _lag_kernel()
    _restore_hist(snapshot)


def lagvalue(t, nr=_MISSING):
    """Return lagged state value(s) at time ``t`` (R ``lagvalue``)."""
    _, _, _, _, lagvalue_kernel = _lag_kernel()
    t = float(np.asarray(t, dtype=float).reshape(()))
    if nr is _MISSING or nr is None:
        nr_arg = None
    elif np.isscalar(nr):
        nr_arg = [int(nr)]
    else:
        nr_arg = [int(x) for x in np.asarray(nr, dtype=int).reshape(-1)]
    out = lagvalue_kernel(t, nr_arg)
    arr = np.asarray(out, dtype=float)
    if nr is _MISSING or nr is None:
        return arr
    if np.isscalar(nr):
        return float(arr.reshape(-1)[0])
    return arr
