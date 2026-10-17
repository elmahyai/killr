"""Aquaphy algal model derivative from deSolve ``R/Aquaphy.R`` and ``src/ex_Aquaphy.c``."""

from __future__ import annotations

import numpy as np

from aquaphy import aquaphy_eval_py as _aquaphy_eval
from aquaphy import aquaphy_pack_py as _aquaphy_pack

_STATE_NAMES = ("DIN", "PROTEIN", "RESERVE", "LMW")
_OUT_NAMES = (
    "PAR",
    "TotalN",
    "PhotoSynthesis",
    "NCratio",
    "ChlCratio",
    "Chlorophyll",
)
_PARM_NAMES = (
    "maxPhotoSynt",
    "rMortPHY",
    "alpha",
    "pExudation",
    "maxProteinSynt",
    "ksDIN",
    "minpLMW",
    "maxpLMW",
    "minQuotum",
    "maxStorage",
    "respirationRate",
    "pResp",
    "catabolismRate",
    "dilutionRate",
    "rNCProtein",
    "inputDIN",
    "rChlN",
    "parMean",
    "dayLength",
)


def _as_state(y):
    if isinstance(y, dict):
        arr = np.asarray([y[name] for name in _STATE_NAMES], dtype=np.float64)
    else:
        arr = np.asarray(y, dtype=np.float64).reshape(-1)
    if arr.size != 4:
        raise ValueError("length of state variable vector should be 4")
    return arr


def _as_parms(parms):
    if isinstance(parms, dict):
        if len(parms) != 19:
            raise ValueError("length of parameter vector should be 19")
        arr = np.asarray([parms[name] for name in _PARM_NAMES], dtype=np.float64)
    else:
        arr = np.asarray(parms, dtype=np.float64).reshape(-1)
        if arr.size != 19:
            raise ValueError("length of parameter vector should be 19")
    return arr


def aquaphy_eval(time, y, parms, par=None):
    """Evaluate ``aquaphy`` at one time (deSolve ``DLLfunc`` equivalent).

    Returns a dict with ``delta`` (state derivatives) and ``var`` (model outputs),
    with names matching deSolve.
    """
    state = _as_state(y)
    p = _as_parms(parms)
    result = _aquaphy_eval(float(time), state, p, par)
    delta = np.asarray(result["delta"], dtype=np.float64)
    var = np.asarray(result["var"], dtype=np.float64)
    return {
        "dy": delta,
        "delta": delta,
        "var": var,
        "names": {"dy": list(_STATE_NAMES), "var": list(_OUT_NAMES)},
    }


def aquaphy(times, y, parms, PAR=None, **kwargs):
    """Aquaphy wrapper matching R validation; integration is not translated."""
    _as_state(y)
    _as_parms(parms)
    if kwargs:
        raise NotImplementedError(
            "aquaphy time integration requires ode, which is not translated"
        )
    times_arr = np.atleast_1d(np.asarray(times, dtype=np.float64))
    if times_arr.size != 1:
        raise NotImplementedError(
            "aquaphy time integration requires ode, which is not translated"
        )
    if PAR is not None:
        raise NotImplementedError(
            "aquaphy with PAR forcings requires ode, which is not translated"
        )
    return aquaphy_eval(float(times_arr[0]), y, parms, par=None)


def aquaphy_derivative_pack(times, y, parms, par=None):
    """Flattened ``delta`` and ``var`` at each time, for proofs."""
    state = _as_state(y)
    p = _as_parms(parms)
    times_list = [float(t) for t in np.atleast_1d(times)]
    packed = _aquaphy_pack(times_list, state, p, par)
    return np.asarray(packed, dtype=np.float64)
