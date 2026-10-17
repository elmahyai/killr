import json
import statistics
import time

import numpy as np

from nloptr import (
    auglag, bobyqa, ccsaq, check_derivatives, cobyla, crs2lm, direct, directL,
    is_nloptr, isres, lbfgs, mlsl, mma, neldermead, newuoa, nl_grad, nl_jacobian,
    nl_opts, nloptr, nloptr_get_default_options, nloptr_print_options, sbplx,
    slsqp, stogo, tnewton, varmetric,
)

def one():
    fn = lambda x: x[0] ** 2 + x[1] ** 2
    gr = lambda x: 2 * np.asarray(x, dtype=float)
    hin = lambda x: 1 - x[0] - x[1]
    S = ccsaq([0.5, 0.5], fn, gr=gr, hin=hin, lower=[0, 0], upper=[2, 2], deprecated_behavior=False, control={"xtol_rel": 1e-8})
    return np.array([S["par"][0], S["par"][1], S["value"], S["convergence"]])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

def encode(item):
    if isinstance(item, bool):
        return "true" if item else "false"
    if isinstance(item, str):
        return json.dumps(item)
    array = np.atleast_1d(np.asarray(item, dtype=float))
    return "[" + ",".join("%.17g" % float(part) for part in array.ravel()) + "]"

print("{\"value\":%s,\"median_ms\":%.17g}" % (encode(value), statistics.median(elapsed)))
