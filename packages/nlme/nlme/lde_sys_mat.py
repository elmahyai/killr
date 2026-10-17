"""Linear differential-equation system matrix (nlme ``LDEsysMat``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def _incidence_columns(incidence: object) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if isinstance(incidence, Mapping):
        try:
            ff = np.asarray(incidence["From"], dtype=np.int64)
            tt = np.asarray(incidence["To"], dtype=np.int64)
            par = np.asarray(incidence["Par"], dtype=np.int64)
        except KeyError as exc:
            raise ValueError('incidence must have columns "From", "To", and "Par"') from exc
        return ff, tt, par

    arr = np.asarray(incidence)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError("incidence must be a matrix with columns From, To, and Par")
    colnames = getattr(incidence, "colnames", None)
    if colnames is None:
        raise ValueError('incidence must have colnames "From", "To", and "Par"')
    names = list(colnames)
    try:
        ff = arr[:, names.index("From")].astype(np.int64, copy=False)
        tt = arr[:, names.index("To")].astype(np.int64, copy=False)
        par = arr[:, names.index("Par")].astype(np.int64, copy=False)
    except ValueError as exc:
        raise ValueError('incidence must have columns "From", "To", and "Par"') from exc
    return ff, tt, par


def LDEsysMat(pars: Sequence[float], incidence: object) -> np.ndarray:
    """Build the compartment-model system matrix from parameters and incidence."""
    pars_arr = np.asarray(pars, dtype=np.float64)
    ff, tt, par = _incidence_columns(incidence)
    pp = pars_arr[par - 1]
    n = int(max(ff.max(initial=0), tt.max(initial=0)))
    val = np.zeros((n, n), dtype=np.float64)
    if n > 0:
        out_sums = np.bincount((ff - 1).astype(np.int64), weights=pp, minlength=n)
        np.fill_diagonal(val, -out_sums)
        flow = tt > 0
        if np.any(flow):
            to_idx = (tt[flow] - 1).astype(np.int64)
            from_idx = (ff[flow] - 1).astype(np.int64)
            val[to_idx, from_idx] = pp[flow]
    return val
