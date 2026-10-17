"""Control lists for the cumulative link fitters."""

import math
import sys


def _match(value, choices, name):
    if value is None:
        return choices[0]
    hits = [choice for choice in choices if choice.startswith(str(value))]
    if len(hits) != 1:
        raise ValueError(f"{name} must be one of {choices}")
    return hits[0]


def clm_control(
    method="Newton",
    sign_location="negative",
    sign_nominal="positive",
    trace=0,
    max_iter=100,
    grad_tol=1e-6,
    max_line_iter=15,
    rel_tol=1e-6,
    tol=None,
    max_mod_iter=5,
    convergence="warn",
    extra=None,
):
    """Controls for clm. Dots in the R function land in extra when the method is an optimizer."""
    method = _match(
        method, ("Newton", "model.frame", "design", "ucminf", "nlminb", "optim"), "method"
    )
    convergence = _match(convergence, ("warn", "silent", "stop", "message"), "convergence")
    sign_location = _match(sign_location, ("negative", "positive"), "sign.location")
    sign_nominal = _match(sign_nominal, ("positive", "negative"), "sign.nominal")
    if tol is None:
        tol = math.sqrt(sys.float_info.epsilon)
    numbers = (max_iter, grad_tol, max_line_iter, rel_tol, tol, max_mod_iter)
    if not all(isinstance(number, (int, float)) and math.isfinite(number) for number in numbers):
        raise ValueError(
            "maxIter, gradTol, relTol, tol, maxModIter and maxLineIter should all be numeric"
        )
    ctrl = {
        "method": method,
        "sign.location": sign_location,
        "sign.nominal": sign_nominal,
        "convergence": convergence,
        "trace": int(trace),
        "maxIter": int(max_iter),
        "gradTol": float(grad_tol),
        "relTol": float(rel_tol),
        "tol": float(tol),
        "maxLineIter": int(max_line_iter),
        "maxModIter": int(max_mod_iter),
    }
    if method in ("ucminf", "nlminb", "optim"):
        nested = {"trace": int(abs(trace))}
        if extra:
            nested.update(extra)
        ctrl["ctrl"] = nested
    return ctrl


def clmm_control(
    method="nlminb",
    trace=0,
    max_iter=50,
    grad_tol=1e-4,
    max_line_iter=50,
    use_matrix=False,
    inner_ctrl="warnOnly",
    check_ranef="warn",
    extra=None,
):
    """Controls for clmm. useMatrix stays false unless the caller asks."""
    method = _match(method, ("nlminb", "ucminf", "model.frame"), "method")
    inner_ctrl = _match(inner_ctrl, ("warnOnly", "noWarn", "giveError"), "innerCtrl")
    check_ranef = _match(check_ranef, ("warn", "error", "message"), "checkRanef")
    use_matrix = bool(use_matrix)
    ctrl = {
        "trace": 1 if trace < 0 else 0,
        "maxIter": max_iter,
        "gradTol": grad_tol,
        "maxLineIter": max_line_iter,
        "innerCtrl": inner_ctrl,
    }
    opt = {"trace": abs(trace)}
    if extra:
        opt.update(extra)
    numeric = (ctrl["maxIter"], ctrl["gradTol"], ctrl["maxLineIter"], ctrl["trace"])
    if not all(isinstance(number, (int, float)) and math.isfinite(number) for number in numeric):
        raise ValueError("maxIter, gradTol, maxLineIter and trace should all be numeric")
    if any(number <= 0 for number in (ctrl["maxIter"], ctrl["gradTol"], ctrl["maxLineIter"])):
        raise ValueError("maxIter, gradTol and maxLineIter have to be > 0")
    if method == "ucminf" and "grtol" not in opt:
        opt["grtol"] = 1e-5
    if method == "ucminf" and "grad" not in opt:
        opt["grad"] = "central"
    return {
        "method": method,
        "useMatrix": use_matrix,
        "ctrl": ctrl,
        "optCtrl": opt,
        "checkRanef": check_ranef,
    }


def clm2_control(
    method="ucminf",
    conv_tol=1e-4,
    trace=0,
    max_iter=100,
    grad_tol=1e-5,
    max_line_iter=10,
    extra=None,
):
    """Controls for clm2. The default method is ucminf."""
    method = _match(method, ("ucminf", "Newton", "nlminb", "optim", "model.frame"), "method")
    if method == "Newton":
        ctrl = {
            "convTol": conv_tol,
            "trace": trace,
            "maxIter": max_iter,
            "gradTol": grad_tol,
            "maxLineIter": max_line_iter,
        }
    else:
        ctrl = {"trace": abs(trace)}
        if extra:
            ctrl.update(extra)
    if not all(
        isinstance(number, (int, float)) and math.isfinite(number)
        for number in (max_iter, grad_tol, max_line_iter, conv_tol)
    ):
        raise ValueError("maxIter, gradTol, maxLineIter, convTol should all be numeric")
    if conv_tol <= 0:
        raise ValueError("convTol should be > 0")
    if method == "ucminf" and "grtol" not in ctrl:
        ctrl["grtol"] = grad_tol
    return {"method": method, "convTol": conv_tol, "ctrl": ctrl}


def clmm2_control(
    method="ucminf",
    trace=0,
    max_iter=50,
    grad_tol=1e-4,
    max_line_iter=50,
    inner_ctrl="warnOnly",
    extra=None,
):
    """Controls for clmm2."""
    method = _match(method, ("ucminf", "nlminb", "model.frame"), "method")
    inner_ctrl = _match(inner_ctrl, ("warnOnly", "noWarn", "giveError"), "innerCtrl")
    ctrl = {
        "trace": 1 if trace < 0 else 0,
        "maxIter": max_iter,
        "gradTol": grad_tol,
        "maxLineIter": max_line_iter,
        "innerCtrl": inner_ctrl,
    }
    opt = {"trace": abs(trace)}
    if extra:
        opt.update(extra)
    if not all(
        isinstance(number, (int, float)) and math.isfinite(float(number))
        for number in (ctrl["maxIter"], ctrl["gradTol"], ctrl["maxLineIter"], trace)
    ):
        raise ValueError("maxIter, gradTol, maxLineIter and trace should all be numeric")
    if any(number <= 0 for number in (ctrl["maxIter"], ctrl["gradTol"], ctrl["maxLineIter"])):
        raise ValueError("maxIter, gradTol and maxLineIter have to be > 0")
    if method == "ucminf" and "grtol" not in opt:
        opt["grtol"] = 1e-5
    if method == "ucminf" and "grad" not in opt:
        opt["grad"] = "central"
    return {"method": method, "ctrl": ctrl, "optCtrl": opt}
