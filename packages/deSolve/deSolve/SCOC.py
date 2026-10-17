"""Sediment model of oxygen consumption (deSolve SCOC)."""

from __future__ import annotations

import warnings

import numpy as np
from scipy import integrate

from deSolve.rk4 import DeSolveMatrix, _numeric_vector

try:
    from scoc import scocder_py as _scocder
except ImportError:
    _scocder = None


def _require_scocder():
    if _scocder is None:
        raise ImportError("scoc extension module is not installed")


def _as_flux(flux):
    array = np.asarray(flux, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError("forcing function data sets should consist of two-column matrix")
    return array.copy()


def _prepare_forcings(flux, times, fcontrol=None):
    """Mirror deSolve checkforcings for one two-column forcing matrix."""
    con = {"method": "linear", "rule": 2, "f": 0, "ties": "ordered"}
    if fcontrol:
        con.update(fcontrol)
    method_names = ("linear", "constant")
    if con["method"] not in method_names:
        raise ValueError("invalid interpolation method for forcing functions")
    fmethod = method_names.index(con["method"]) + 1

    forcings = _as_flux(flux)
    r_t = (float(np.min(times)), float(np.max(times)))
    t = forcings[:, 0]
    if t[0] > r_t[0]:
        if con["rule"] == 2:
            forcings = np.vstack([[r_t[0], forcings[0, 1]], forcings])
        else:
            raise ValueError("extrapolating forcing function data sets to first timepoint 1")
    if forcings[-1, 0] < r_t[1]:
        if con["rule"] == 2:
            forcings = np.vstack([forcings, [r_t[1], forcings[-1, 1]]])
        else:
            raise ValueError("extrapolating forcing function data sets to last timepoint 1")

    if con["ties"] != "ordered":
        x = forcings[:, 0]
        y = forcings[:, 1]
        ux = np.unique(x)
        if ux.size < x.size:
            y = np.array([y[x == xi].mean() for xi in ux])
            x = ux
        else:
            order = np.argsort(x)
            x = x[order]
            y = y[order]
        forcings = np.column_stack([x, y])

    if fmethod == 2 and con["f"] != 0:
        y = forcings[:, 1]
        yy = np.r_[y[1:], y[-1]]
        forcings[:, 1] = (1.0 - con["f"]) * y + con["f"] * yy

    tvec = forcings[:, 0]
    fvec = forcings[:, 1]
    return tvec, fvec, fmethod


class _ForcingState:
    """deSolve updatedeforc for a single forcing series."""

    __slots__ = ("tvec", "fvec", "fmethod", "findex", "intpol", "maxindex")

    def __init__(self, tvec, fvec, fmethod):
        self.tvec = tvec
        self.fvec = fvec
        self.fmethod = fmethod
        self.findex = 0
        self.maxindex = len(tvec) - 2
        self.intpol = 0.0
        if fmethod == 1 and len(tvec) > 1:
            self.intpol = (fvec[1] - fvec[0]) / (tvec[1] - tvec[0])

    def value_at(self, time: float) -> float:
        tvec = self.tvec
        fvec = self.fvec
        ii = self.findex
        zerograd = False
        while time > tvec[ii + 1]:
            if ii + 2 > self.maxindex:
                zerograd = True
                break
            ii += 1
        while time < tvec[ii]:
            ii -= 1
        if ii != self.findex:
            self.findex = ii
            if not zerograd and self.fmethod == 1:
                self.intpol = (fvec[ii + 1] - fvec[ii]) / (tvec[ii + 1] - tvec[ii])
            else:
                self.intpol = 0.0
        return fvec[ii] + self.intpol * (time - tvec[ii])


def _default_state(flux, k):
    x = np.arange(1, 366, dtype=np.float64)
    flux = _as_flux(flux)
    mean_depo = float(np.mean(np.interp(x, flux[:, 0], flux[:, 1])))
    return mean_depo / k


def _as_parms(parms):
    if isinstance(parms, dict):
        values = np.asarray(list(parms.values()), dtype=np.float64)
    else:
        values = np.asarray(parms, dtype=np.float64)
    if values.size != 1:
        raise ValueError("length of parameter vector should be 1")
    return float(values.ravel()[0])


def _as_initial_y(y, flux, k):
    if y is None:
        return _default_state(flux, k)
    values = _numeric_vector(y, "`y' must be numeric")
    if values.size != 1:
        raise ValueError("length of state variable vector should be 1")
    return float(values[0])


def SCOC(times, y=None, parms=None, Flux=None, **kwargs):
    """Integrate the SCOC sediment carbon model."""
    _require_scocder()
    if Flux is None:
        raise TypeError("SCOC() missing required argument: 'Flux'")
    if parms is None:
        raise TypeError("SCOC() missing required argument: 'parms'")

    times = _numeric_vector(times, "`times' must be numeric")
    if times.size < 1:
        raise ValueError("`times' must be NULL or numeric")
    k = _as_parms(parms)
    y0 = _as_initial_y(y, Flux, k)

    fcontrol = kwargs.pop("fcontrol", None)
    if fcontrol is not None and not isinstance(fcontrol, dict):
        fcontrol = dict(fcontrol)
    rtol = float(kwargs.pop("rtol", 1e-6))
    atol = float(kwargs.pop("atol", 1e-6))
    verbose = bool(kwargs.pop("verbose", False))
    kwargs.pop("ynames", None)

    unknown = set(kwargs)
    if unknown:
        warnings.warn(
            f"unused integrator arguments: {', '.join(sorted(unknown))}",
            stacklevel=2,
        )

    tvec, fvec, fmethod = _prepare_forcings(Flux, times, fcontrol)
    forcing = _ForcingState(tvec, fvec, fmethod)

    def rhs(t, state):
        depo = forcing.value_at(float(t))
        ydot, _, _ = _scocder(k, float(state[0]), depo)
        return [ydot]

    sol = integrate.solve_ivp(
        rhs,
        (float(times[0]), float(times[-1])),
        [y0],
        t_eval=times,
        method="LSODA",
        rtol=rtol,
        atol=atol,
    )
    if not sol.success:
        raise RuntimeError(sol.message)

    nt = times.size
    table = np.zeros((nt, 4), dtype=np.float64)
    table[:, 0] = times
    table[:, 1] = sol.y[0]
    for row in range(nt):
        depo = forcing.value_at(float(times[row]))
        _, mineralisation, depo_out = _scocder(k, float(table[row, 1]), depo)
        table[row, 2] = mineralisation
        table[row, 3] = depo_out

    istate = [None] * 21
    istate[0] = 2
    istate[1] = max(int(sol.t.size) - 1, 0)
    istate[2] = int(sol.nfev)
    istate[17] = 5

    result = DeSolveMatrix(
        table,
        ["time", "C", "Mineralisation", "Depo"],
        istate,
        None,
        None,
        None,
    )
    result.type = "vode"
    if verbose:
        print(f"return code: {istate[0]}")
        print(f"function evaluations: {istate[2]}")
    return result
