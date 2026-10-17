import statistics
import time

import numpy as np

from ucminf import ucminf


def one():
    def fR(x):
        return (1 - x[0]) ** 2 + 100 * (x[1] - x[0] ** 2) ** 2

    def gR(x):
        return np.array(
            [
                -400 * x[0] * (x[1] - x[0] * x[0]) - 2 * (1 - x[0]),
                200 * (x[1] - x[0] * x[0]),
            ]
        )

    fit = ucminf(np.array([2.0, 0.5]), fR, gR)
    info = fit.info
    return np.concatenate(
        [
            fit.par,
            [fit.value, fit.convergence, info["maxgradient"], info["laststep"], info["stepmax"], info["neval"]],
            fit.invhessian_lt,
        ]
    )


value = np.ravel(np.asarray(one(), dtype=float), order="F")
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
