"""Lagged state derivatives for delay differential equations (deSolve ``lagderiv``)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_MISSING = object()


def _lagderiv_kernel():
    try:
        from lagderiv import lagderiv_kernel as _kernel
        from lagderiv import restore_hist as _restore_hist
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "lagderiv"))
        from lagderiv import lagderiv_kernel as _kernel
        from lagderiv import restore_hist as _restore_hist
    return _restore_hist, _kernel


def restore_hist(snapshot: dict) -> None:
    """Restore history from an R ``dump_lag_history`` snapshot (proof helper)."""
    _restore_hist, _ = _lagderiv_kernel()
    _restore_hist(snapshot)


def lagderiv(t, nr=_MISSING):
    """Return lagged state derivative(s) at time ``t`` (R ``lagderiv``)."""
    _, lagderiv_kernel = _lagderiv_kernel()
    t = float(np.asarray(t, dtype=float).reshape(()))
    if nr is _MISSING or nr is None:
        nr_arg = None
    elif np.isscalar(nr):
        nr_arg = [int(nr)]
    else:
        nr_arg = [int(x) for x in np.asarray(nr, dtype=int).reshape(-1)]
    out = lagderiv_kernel(t, nr_arg)
    arr = np.asarray(out, dtype=float)
    if nr is _MISSING or nr is None:
        return arr
    if np.isscalar(nr):
        return float(arr.reshape(-1)[0])
    return arr
