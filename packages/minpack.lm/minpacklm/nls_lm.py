"""Levenberg-Marquardt nonlinear least squares (``nls.lm``)."""

from __future__ import annotations

import math
import warnings

import numpy as np

from minpacklm.nls_lm_control import nls_lm_control

_DIGITS = max(3, 7 - 3)


def nls_lm(par, fn, jac=None, lower=None, upper=None, control=None, **kwargs):
    """Minimize the sum of squares of ``fn(par)`` with MINPACK's LM method.

    ``par`` is a numeric vector or a mapping of length-1 parameters. An empty
    ``maxfev`` in ``control`` is filled with ``100 * (len(par) + 1)``. Bounds
    default to ``-inf`` and ``inf``.
    """
    names, start, as_mapping = _as_par(par)
    n = int(start.size)
    lower_v = _as_bound(lower, n, -math.inf, "lower")
    upper_v = _as_bound(upper, n, math.inf, "upper")
    if not np.all(np.isfinite(start)):
        raise ValueError("Non-finite (or null) value for a parameter specified!")

    ctrl = _merge_control(control)
    maxfev = ctrl["maxfev"]
    if _maxfev_empty(maxfev):
        maxfev_value = 100 * (n + 1)
    else:
        maxfev_value = _as_int(maxfev)
    maxiter = _as_int(ctrl["maxiter"])
    if maxiter > 1024:
        warnings.warn("resetting `maxiter' to 1024!", stacklevel=2)
        maxiter = 1024
    nprint = _as_int(ctrl["nprint"])
    diag_values, diag_is_list, mode_user = _as_diag(ctrl["diag"], n)

    holder = {name: float(start[index]) for index, name in enumerate(names)} if as_mapping else None

    def resid(values):
        vector = np.asarray(values, dtype=float)
        argument = _argument(vector, names, holder, as_mapping)
        out = fn(argument, **kwargs)
        return np.asarray(out, dtype=float).reshape(-1)

    jac_fn = None
    if jac is not None:
        def jac_fn(values):
            vector = np.asarray(values, dtype=float)
            argument = _argument(vector, names, holder, as_mapping)
            out = jac(argument, **kwargs)
            return _jac_flat(out)

    import lmdif

    raw = lmdif.solve(
        start.tolist(),
        lower_v.tolist(),
        upper_v.tolist(),
        float(ctrl["ftol"]),
        float(ctrl["ptol"]),
        float(ctrl["gtol"]),
        float(ctrl["epsfcn"]),
        float(ctrl["factor"]),
        int(maxfev_value),
        int(maxiter),
        1 if nprint > 0 else 0,
        diag_values.tolist() if mode_user else None,
        lambda values: resid(values).tolist(),
        None if jac_fn is None else (lambda values: jac_fn(values).tolist()),
    )
    info = int(raw["info"])
    message = str(raw["message"])
    if info < 1 or info > 9:
        which = "lmder" if jac is not None else "lmdif"
        warnings.warn(f"{which}: info = {info}. {message}\n\n", stacklevel=2)

    solved = np.asarray(raw["par"], dtype=float)
    fvec = np.asarray(raw["fvec"], dtype=float)
    hessian = np.asarray(raw["hessian"], dtype=float).reshape((n, n), order="F")
    diag = np.asarray(raw["diag"], dtype=float)
    if diag_is_list:
        diag_out = [float(item) for item in diag]
    else:
        diag_out = diag
    if as_mapping:
        par_out = {name: float(solved[index]) for index, name in enumerate(names)}
    else:
        par_out = solved
        if names:
            par_out = solved.copy()
    result = NlsLmResult(
        par=par_out,
        hessian=hessian,
        fvec=fvec,
        info=info,
        message=message,
        diag=diag_out,
        niter=int(raw["niter"]),
        rsstrace=np.asarray(raw["rsstrace"], dtype=float),
        deviance=float(np.dot(fvec, fvec)),
    )
    result.names = list(names)
    return result


class NlsLmResult(dict):
    """Fit returned by :func:`nls_lm`, with the same component names as R."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __str__(self):
        par = self["par"]
        if isinstance(par, dict):
            values = list(par.values())
        else:
            values = [float(item) for item in np.ravel(par)]
        deviance = format(float(self["deviance"]), f".{_DIGITS}g")
        return (
            "Nonlinear regression via the Levenberg-Marquardt algorithm\n"
            f"parameter estimates: {_tostring(values)} \n"
            f"residual sum-of-squares: {deviance}\n"
            f"reason terminated: {self['message']}\n"
        )


def _tostring(values):
    parts = []
    for value in values:
        number = float(value)
        if math.isfinite(number) and number == math.trunc(number) and abs(number) < 1e15:
            parts.append(str(int(number)))
        else:
            parts.append(format(number, ".7g"))
    return ", ".join(parts)


def _as_par(par):
    if isinstance(par, dict):
        names = list(par.keys())
        values = np.array([float(par[name]) for name in names], dtype=float)
        return names, values, True
    if isinstance(par, np.ndarray):
        values = np.asarray(par, dtype=float).reshape(-1)
        names = list(par.dtype.names) if par.dtype.names else []
        return names, values, False
    if isinstance(par, (list, tuple)):
        if par and isinstance(par[0], (list, tuple)) and len(par[0]) == 2 and isinstance(par[0][0], str):
            names = [item[0] for item in par]
            values = np.array([float(item[1]) for item in par], dtype=float)
            return names, values, True
        values = np.asarray(par, dtype=float).reshape(-1)
        return [], values, False
    values = np.asarray(par, dtype=float).reshape(-1)
    return [], values, False


def _as_bound(bound, n, fill, label):
    if bound is None:
        return np.full(n, fill, dtype=float)
    if isinstance(bound, dict):
        values = np.array([float(item) for item in bound.values()], dtype=float)
    else:
        values = np.asarray(bound, dtype=float).reshape(-1)
    if values.size != n:
        raise ValueError(f"length({label}) must be equal to length(par)")
    return values


def _merge_control(control):
    ctrl = nls_lm_control()
    if control is None:
        return ctrl
    for key, value in dict(control).items():
        ctrl[key] = value
    return ctrl


def _maxfev_empty(value):
    if value is None:
        return True
    if isinstance(value, np.ndarray):
        return value.size == 0
    if isinstance(value, (list, tuple)):
        return len(value) == 0
    return False


def _as_int(value):
    if isinstance(value, np.ndarray):
        if value.size != 1:
            raise ValueError("control value must have length 1")
        value = value.reshape(-1)[0]
    return int(value)


def _as_diag(diag, n):
    if diag is None:
        return np.zeros(n, dtype=float), True, False
    if isinstance(diag, np.ndarray):
        values = np.asarray(diag, dtype=float).reshape(-1)
        return values, False, values.size == n
    if isinstance(diag, (list, tuple)):
        if len(diag) == n:
            return np.array([float(item) for item in diag], dtype=float), True, True
        return np.zeros(n, dtype=float), True, False
    values = np.asarray([float(diag)], dtype=float)
    return values, False, values.size == n


def _argument(vector, names, holder, as_mapping):
    if as_mapping:
        for index, name in enumerate(names):
            holder[name] = float(vector[index])
        return holder
    return vector


def _jac_flat(value):
    array = np.asarray(value, dtype=float)
    if array.ndim == 2:
        return np.ravel(array, order="F")
    return array.reshape(-1)
