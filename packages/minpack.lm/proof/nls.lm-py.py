import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from minpacklm.nls_lm import nls_lm
from minpacklm.nls_lm_control import nls_lm_control


def fn(p):
    return np.array([1.0 - p[0], 10.0 * (p[1] - p[0] ** 2)])


def jac(p):
    return np.array([-1.0, -20.0 * p[0], 0.0, 10.0])


def fn_list(p):
    return np.array([1.0 - p["a"], 10.0 * (p["b"] - p["a"] ** 2)])


def pack(fit):
    diag = fit["diag"]
    diag_is_list = isinstance(diag, list)
    if isinstance(diag, np.ndarray):
        diag_vals = [float(item) for item in np.ravel(diag)]
    else:
        diag_vals = [float(item) for item in diag]
    par = fit["par"]
    if isinstance(par, dict):
        par_vals = [float(par[name]) for name in par]
    else:
        par_vals = [float(item) for item in np.ravel(par)]
    hessian = np.asarray(fit["hessian"], dtype=float).ravel(order="F")
    return [
        *par_vals,
        *[float(item) for item in hessian],
        *[float(item) for item in np.ravel(fit["fvec"])],
        float(fit["info"]),
        float(fit["niter"]),
        float(fit["deviance"]),
        1.0 if diag_is_list else 0.0,
        *diag_vals,
        *[float(item) for item in np.ravel(fit["rsstrace"])[: int(fit["niter"])]],
    ]


def one():
    finite = nls_lm(np.array([-1.2, 1.0]), fn)
    analytic = nls_lm(np.array([-1.2, 1.0]), fn, jac=jac)
    bounded = nls_lm(
        np.array([1.0, 1.0]),
        fn,
        lower=np.array([0.0, 0.0]),
        upper=np.array([0.5, 2.0]),
    )
    stopped = nls_lm(
        np.array([-1.2, 1.0]),
        fn,
        control=nls_lm_control(maxiter=2),
    )
    scaled = nls_lm(
        np.array([-1.2, 1.0]),
        fn,
        control=nls_lm_control(diag=np.array([1.0, 2.0])),
    )
    named = nls_lm({"a": -1.2, "b": 1.0}, fn_list)
    if finite["message"] != "Relative error between `par' and the solution is at most `ptol'.":
        raise AssertionError(finite["message"])
    if "gtol" not in analytic["message"]:
        raise AssertionError(analytic["message"])
    if int(stopped["info"]) != -1 or "maxiter" not in stopped["message"]:
        raise AssertionError(stopped["message"])
    packed = []
    for fit in (finite, analytic, bounded, stopped, scaled, named):
        packed.extend(pack(fit))
    return packed


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (
        ",".join("%.17g" % float(part) for part in value),
        statistics.median(elapsed),
    )
)
