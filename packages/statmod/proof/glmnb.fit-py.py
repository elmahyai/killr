import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.glmnb_fit import glmnb_fit


def _collect(fit):
    return np.concatenate(
        [
            fit["coefficients"],
            fit["fitted.values"],
            np.array([fit["deviance"], fit["iter"]], dtype=float),
        ]
    )


def one():
    x10 = np.column_stack(
        [
            np.ones(10),
            np.arange(1, 11, dtype=float),
            np.array([0.5, 1.1, -0.2, 0.8, 1.4, -0.5, 0.3, 1.2, -0.1, 0.9], dtype=float),
        ]
    )
    y10 = np.array([3, 5, 2, 7, 4, 1, 6, 2, 8, 9], dtype=float)
    f1 = glmnb_fit(x10, y10, dispersion=0.2)
    x8 = np.column_stack([np.ones(8), np.linspace(0.2, 1.5, 8)])
    y8 = np.array([0, 2, 5, 1, 8, 3, 0, 4], dtype=float)
    w8 = np.array([1, 1, 2, 1, 1, 0.5, 1, 1], dtype=float)
    off8 = np.log(np.array([10, 12, 11, 9, 15, 13, 10, 14], dtype=float))
    f2 = glmnb_fit(
        x8,
        y8,
        dispersion=np.full(8, 0.05),
        weights=w8,
        offset=off8,
        start_method="log(y)",
        tol=1e-8,
    )
    x6 = np.column_stack([np.ones(6), np.arange(1, 7, dtype=float)])
    y6 = np.array([2, 4, 6, 3, 8, 5], dtype=float)
    f3 = glmnb_fit(x6, y6, dispersion=0.1, coef_start=np.array([0.1, 0.05]), maxit=30)
    return np.concatenate([_collect(f1), _collect(f2), _collect(f3)])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
