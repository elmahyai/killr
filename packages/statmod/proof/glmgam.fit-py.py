import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.glmgam_fit import glmgam_fit


def one():
    y10 = np.array([3.2, 5.1, 4.8, 6.3, 2.9, 7.4, 5.5, 4.1, 6.8, 3.7], dtype=float)
    x10 = np.column_stack(
        [
            np.ones(10),
            np.arange(1, 11, dtype=float),
            np.array([0.5, 1.1, -0.2, 0.8, 1.4, -0.5, 0.3, 1.2, -0.1, 0.9], dtype=float),
        ]
    )
    y6 = np.array([1.2, 0.8, 2.5, 3.1, 0.4, 1.9], dtype=float)
    x6 = np.column_stack(
        [
            np.ones(6),
            np.array([2, -1, 3, 0.5, -2, 1.5], dtype=float),
            np.array([-0.3, 1.1, 0.7, -0.8, 0.2, 1.3], dtype=float),
        ]
    )
    start = np.array([0.5, 0.05, 0.1], dtype=float)
    f1 = glmgam_fit(x10, y10)
    f2 = glmgam_fit(x6, y6, coef_start=start, tol=1e-8, maxit=80)
    return np.concatenate(
        [
            f1["coefficients"],
            f1["fitted.values"],
            np.array([f1["deviance"], f1["iter"]], dtype=float),
            f2["coefficients"],
            f2["fitted.values"],
            np.array([f2["deviance"], f2["iter"]], dtype=float),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
