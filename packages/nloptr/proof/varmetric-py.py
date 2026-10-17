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
    def flb(x):
        x = np.asarray(x, dtype=float)
        prev = np.concatenate([[1.0], x[:-1]])
        w = np.array([1.0] + [4.0] * (len(x) - 1))
        return float(np.sum(w * (x - prev ** 2) ** 2))
    S = varmetric(np.full(5, 3.0), flb, lower=np.full(5, 2.0), upper=np.full(5, 4.0), control={"xtol_rel": 1e-8})
    return np.concatenate([S["par"], [S["value"], S["convergence"]]])

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
