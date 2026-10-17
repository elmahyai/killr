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
    cd = check_derivatives(np.arange(1, 6, dtype=float), lambda x: float(np.sum(np.asarray(x) ** 2)), lambda x: 2 * np.asarray(x, dtype=float), check_derivatives_print="none")
    return np.concatenate([np.ravel(cd["analytic"]), np.ravel(cd["finite_difference"]), np.ravel(cd["relative_error"])])

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
