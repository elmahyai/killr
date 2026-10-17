"""BBoptim, BBsolve, and multiStart."""

import numpy as np

from BB.sane import dfsane
from BB.spg import _unknown, spg


def _expand(method, memory, nm=None):
    methods = np.atleast_1d(np.asarray(method, dtype=float))
    memories = np.atleast_1d(np.asarray(memory, dtype=float))
    rows = []
    if nm is None:
        for item in memories:
            for name in methods:
                rows.append((float(name), float(item)))
        return rows
    flags = np.atleast_1d(np.asarray(nm))
    for flag in flags:
        for item in memories:
            for name in methods:
                rows.append((float(name), float(item), bool(flag)))
    return rows


def bb_optim(
    par,
    fn,
    gr=None,
    method=(2, 3, 1),
    lower=-np.inf,
    upper=np.inf,
    project=None,
    projectArgs=None,
    control=None,
    quiet=False,
    **kwargs,
):
    """Try several spectral-gradient settings and keep the first success."""
    allowed = [
        "maxit", "M", "ftol", "gtol", "maxfeval", "maximize", "trace", "triter",
        "eps", "checkGrad", "checkGrad.tol",
    ]
    _unknown(control, allowed)
    point = np.asarray(par, dtype=float)
    if point.ndim == 2:
        raise ValueError("argument par should not be a matrix in BBoptim.")
    ctrl = {
        "maxit": 1500, "M": (50, 10), "ftol": 1e-10, "gtol": 1e-5, "maxfeval": 10000,
        "maximize": False, "trace": True, "triter": 10, "eps": 1e-7,
        "checkGrad": None, "checkGrad.tol": 1e-6,
    }
    if control:
        ctrl.update(control)
    best = None
    best_value = np.inf
    feval = 0
    iteration = 0
    last_error = None
    for name, memory in _expand(method, ctrl["M"]):
        try:
            temp = spg(
                point, fn, gr=gr, method=name, lower=lower, upper=upper,
                project=project, projectArgs=projectArgs,
                control={
                    "M": memory, "maxit": ctrl["maxit"], "maximize": ctrl["maximize"],
                    "trace": ctrl["trace"], "triter": ctrl["triter"],
                    "maxfeval": ctrl["maxfeval"], "eps": ctrl["eps"],
                    "gtol": ctrl["gtol"], "ftol": ctrl["ftol"],
                    "checkGrad": ctrl["checkGrad"],
                },
                quiet=quiet, alertConvergence=False, **kwargs,
            )
        except Exception as exc:
            last_error = exc
            continue
        feval += temp["feval"]
        iteration += temp["iter"]
        if temp["convergence"] == 0:
            temp["feval"] = feval
            temp["iter"] = iteration
            temp["cpar"] = np.array([name, memory])
            best = temp
            break
        if temp["value"] < best_value:
            best_value = temp["value"]
            temp["feval"] = feval
            temp["iter"] = iteration
            temp["cpar"] = np.array([name, memory])
            best = temp
    if best is None:
        raise ValueError("All calls to spg failed. Last error: " + str(last_error))
    if not quiet:
        if best["convergence"] != 0:
            print("  Unsuccessful convergence.")
        else:
            print("  Successful convergence.")
    return best


def bb_solve(par, fn, method=(2, 3, 1), control=None, quiet=False, **kwargs):
    """Try several DF-SANE settings and keep the first success."""
    allowed = ["maxit", "M", "tol", "trace", "triter", "noimp", "NM"]
    _unknown(control, allowed)
    point = np.asarray(par, dtype=float)
    if point.ndim == 2:
        raise ValueError("argument par should not be a matrix in BBsolve.")
    point = point.reshape(-1)
    ctrl = {
        "maxit": 1500, "M": (50, 10), "tol": 1e-7, "trace": False, "triter": 10,
        "noimp": 100, "NM": (True, False),
    }
    if control:
        ctrl.update(control)
    use_nm = ctrl["NM"] if 1 < point.size <= 20 else False
    best = None
    best_value = np.inf
    feval = 0
    iteration = 0
    for name, memory, nm in _expand(method, ctrl["M"], use_nm):
        try:
            temp = dfsane(
                point, fn, method=name,
                control={
                    "M": memory, "NM": nm, "maxit": ctrl["maxit"], "tol": ctrl["tol"],
                    "trace": ctrl["trace"], "triter": ctrl["triter"], "noimp": ctrl["noimp"],
                },
                quiet=quiet, alertConvergence=False, **kwargs,
            )
        except Exception:
            continue
        feval += temp["feval"]
        iteration += temp["iter"]
        if temp["convergence"] == 0:
            temp["feval"] = feval
            temp["iter"] = iteration
            temp["cpar"] = np.array([name, memory, 1.0 if nm else 0.0])
            best = temp
            break
        if temp["residual"] < best_value:
            best_value = temp["residual"]
            temp["feval"] = feval
            temp["iter"] = iteration
            temp["cpar"] = np.array([name, memory, 1.0 if nm else 0.0])
            best = temp
    if not quiet:
        if best["convergence"] != 0:
            print("  Unsuccessful convergence.")
        else:
            print("  Successful convergence.")
    return best


def _match_action(action):
    choices = ("solve", "optimize")
    if action is None:
        return "solve"
    if isinstance(action, (list, tuple)):
        action = action[0]
    text = str(action)
    hits = [choice for choice in choices if choice.startswith(text)]
    if len(hits) != 1:
        raise ValueError("action should be one of " + ", ".join(repr(choice) for choice in choices))
    return hits[0]


def multi_start(
    par,
    fn,
    gr=None,
    action=("solve", "optimize"),
    method=(2, 3, 1),
    lower=-np.inf,
    upper=np.inf,
    project=None,
    projectArgs=None,
    control=None,
    quiet=False,
    details=False,
    **kwargs,
):
    """Run BBsolve or BBoptim from each row of starting values."""
    matrix = np.asarray(par, dtype=float)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    chosen = _match_action(action)
    converged = np.zeros(matrix.shape[0], dtype=bool)
    values = np.full(matrix.shape[0], np.nan)
    points = np.full(matrix.shape, np.nan)
    saved = []
    for k in range(matrix.shape[0]):
        if not quiet:
            print("Parameter set : ", k + 1, "... ")
        try:
            if chosen == "solve":
                answer = bb_solve(matrix[k], fn, method=method, control=control, quiet=quiet, **kwargs)
            else:
                answer = bb_optim(
                    matrix[k], fn, gr=gr, method=method, lower=lower, upper=upper,
                    project=project, projectArgs=projectArgs, control=control, quiet=quiet, **kwargs,
                )
        except Exception:
            continue
        converged[k] = answer["convergence"] == 0
        values[k] = answer["residual"] if chosen == "solve" else answer["value"]
        points[k] = answer["par"]
        if details:
            saved.append(answer)
    result = {"par": points, "fvalue": values, "converged": converged}
    if details:
        result["details"] = saved
    return result
