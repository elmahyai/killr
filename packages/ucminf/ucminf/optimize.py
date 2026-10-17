"""Quasi-Newton unconstrained minimization from ucminf 1.2.3."""

import math

import numpy as np

_MESSAGES = {
    1: "Stopped by small gradient (grtol).",
    2: "Stopped by small step (xtol).",
    3: "Stopped by function evaluation limit (maxeval)",
    4: "Stopped by zero step from line search",
    -2: "Computation did not start: length(par) = 0.",
    -4: "Computation did not start: stepmax is too small.",
    -5: "Computation did not start: grtol or xtol <= 0.",
    -6: "Computation did not start: maxeval <= 0.",
    -7: "Computation did not start: given hessian not pos. definite.",
    -8: "Computation did not start: iw too small.",
}

_CONTROLS = {
    "trace": 0,
    "grtol": 1e-6,
    "xtol": 1e-12,
    "stepmax": 1,
    "maxeval": 500,
    "grad": "forward",
    "gradstep": (1e-6, 1e-8),
    "invhessian.lt": None,
}


class UcminfResult:
    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __repr__(self):
        parts = [f"par={self.par}", f"value={self.value}", f"convergence={self.convergence}"]
        return "UcminfResult(" + ", ".join(parts) + ")"


def _workspace(n):
    half = math.ceil(max(n + 1, (n + 11) / 2))
    return n * half + 10


def _symmetrize(lower, n):
    column = np.arange(1, n * n + 1).reshape((n, n), order="F")
    row = np.arange(1, n * n + 1).reshape((n, n), order="C")
    mask = (-row + column) <= 0
    cov = np.zeros((n, n))
    cov[mask] = lower
    return cov.T + cov - np.diag(np.diag(cov))


def ucminf(par, fn, gr=None, control=None, hessian=0, **kwargs):
    """Minimize fn starting at par. The default check is the Rosenbrock function."""
    if control is None:
        control = {}
    unknown = [name for name in control if name not in _CONTROLS]
    if unknown:
        raise ValueError("unknown control: " + ", ".join(unknown))
    options = dict(_CONTROLS)
    options.update(control)
    gradstep = tuple(options["gradstep"])
    if len(gradstep) != 2 or options["grad"] not in ("forward", "central"):
        raise ValueError("gradstep must have length 2 and grad must be forward or central")
    if hessian is True:
        hessian = 1
    elif hessian is False:
        hessian = 0
    if isinstance(par, dict):
        names = list(par.keys())
        start = np.asarray(list(par.values()), dtype=float).reshape(-1)
    else:
        names = None
        start = np.asarray(par, dtype=float).reshape(-1)
    n = int(start.size)
    iw = _workspace(n)
    w = np.zeros(iw)
    if options["invhessian.lt"] is not None:
        triangle = np.asarray(options["invhessian.lt"], dtype=float).reshape(-1)
        w[4 * n : 4 * n + triangle.size] = triangle
    icontr = 1 + int(options["trace"] > 0) + 2 * int(options["invhessian.lt"] is not None)
    grad_mode = 0 if gr is not None else (1 if options["grad"] == "forward" else 2)

    def objective(x):
        value = fn(np.asarray(x, dtype=float), **kwargs)
        return float(value)

    def gradient(x):
        return [float(part) for part in np.asarray(gr(np.asarray(x, dtype=float), **kwargs), dtype=float).reshape(-1)]

    import ucminf_engine

    updated, convergence, value, _maxgradient, neval, w, stepmax = ucminf_engine.ucminf(
        start.tolist(),
        [float(options["grtol"]), float(options["xtol"])],
        float(options["stepmax"]),
        int(options["maxeval"]),
        w.tolist(),
        int(icontr),
        int(grad_mode),
        [float(gradstep[0]), float(gradstep[1])],
        objective,
        None if gr is None else gradient,
    )
    w = np.asarray(w, dtype=float)
    updated = np.asarray(updated, dtype=float)
    result = UcminfResult(
        par=updated,
        value=float(value),
        convergence=int(convergence),
        message=_MESSAGES.get(int(convergence), ""),
    )
    if convergence > 0:
        triangle = w[4 * n : 4 * n + n * (n + 1) // 2]
        if hessian == 1:
            from numderiv import hessian as numeric_hessian

            result.hessian = numeric_hessian(lambda point: fn(point, **kwargs), updated, method="Richardson")
        if hessian in (2, 3):
            cov = _symmetrize(triangle, n)
            result.invhessian = cov
        if hessian == 3:
            result.hessian = np.linalg.inv(result.invhessian)
        result.invhessian_lt = triangle
        result.info = {
            "maxgradient": float(w[1]),
            "laststep": float(w[2]),
            "stepmax": float(stepmax),
            "neval": int(neval),
        }
    if isinstance(names, list) and names and len(names) == n:
        result.par_names = names
    return result
