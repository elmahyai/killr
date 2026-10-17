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
    def fphv(x):
        return 100 * (x[2] - 10 * np.atan2(x[1], x[0]) / (2 * np.pi)) ** 2 + (np.sqrt(x[0] ** 2 + x[1] ** 2) - 1) ** 2 + x[2] ** 2
    S = sbplx([-1.0, 0.0, 0.0], fphv)
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
