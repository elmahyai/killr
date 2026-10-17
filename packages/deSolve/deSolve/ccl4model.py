"""CCl4 inhalation model from deSolve (compiled dynamics in ``ccl4model`` crate)."""

from __future__ import annotations

import numpy as np
from ccl4model import derivs_ccl4, init_ccl4

from deSolve.rk4 import rk4

_STATE_NAMES = ("AI", "AAM", "AT", "AF", "AL", "CLT", "AM")
_PARM_NAMES = (
    "BW",
    "QP",
    "QC",
    "VFC",
    "VLC",
    "VMC",
    "QFC",
    "QLC",
    "QMC",
    "PLA",
    "PFA",
    "PMA",
    "PTA",
    "PB",
    "MW",
    "VMAX",
    "KM",
    "CONC",
    "KL",
    "RATS",
    "VCHC",
)


def _as_parm_vector(parms) -> np.ndarray:
    if isinstance(parms, dict):
        if len(parms) != 21:
            raise ValueError("length of parameter vector should be 21")
        if all(name in parms for name in _PARM_NAMES):
            values = [float(parms[name]) for name in _PARM_NAMES]
        else:
            values = [float(value) for value in parms.values()]
        return np.asarray(values, dtype=np.float64)
    array = np.asarray(parms, dtype=np.float64).reshape(-1)
    if array.size != 21:
        raise ValueError("length of parameter vector should be 21")
    return array


def _as_state_vector(y) -> np.ndarray:
    if isinstance(y, dict):
        if len(y) != 7:
            raise ValueError("length of state variable vector should be 7")
        if all(name in y for name in _STATE_NAMES):
            values = [float(y[name]) for name in _STATE_NAMES]
        else:
            values = [float(value) for value in y.values()]
            if len(values) != 7:
                raise ValueError("length of state variable vector should be 7")
        return np.asarray(values, dtype=np.float64)
    array = np.asarray(y, dtype=np.float64).reshape(-1)
    if array.size != 7:
        raise ValueError("length of state variable vector should be 7")
    return array


def _named_state(y) -> dict[str, float]:
    values = _as_state_vector(y)
    return {name: float(values[index]) for index, name in enumerate(_STATE_NAMES)}


def _model_func(_t, y, _parms, **_kwargs):
    state = np.asarray(y, dtype=np.float64).reshape(-1)
    ydot, out = derivs_ccl4(float(_t), state)
    return [
        ydot,
        {"DOSE": float(out[0]), "MASS": float(out[1]), "CP": float(out[2])},
    ]


def ccl4model(times, y, parms, **kwargs):
    """Integrate the CCl4 chamber model on ``times``.

    State order is AI, AAM, AT, AF, AL, CLT, AM. ``parms`` holds 21 primary
    parameters in the deSolve order. Integration uses fixed-step ``rk4`` until
    ``ode`` is translated; extra arguments are passed to ``rk4``.
    """
    parm_vec = _as_parm_vector(parms)
    init_ccl4(parm_vec)
    state = _named_state(y)
    return rk4(state, times, _model_func, parm_vec, **kwargs)
