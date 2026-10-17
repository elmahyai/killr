import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.fit_nbp import fit_nbp


def collect(fit):
    return np.concatenate(
        [
            np.array([fit["dispersion"]], dtype=float),
            fit["coefficients"].reshape(-1, order="F"),
            fit["fitted_values"].reshape(-1, order="F"),
        ]
    )


def one():
    y_small = np.array([3, 5, 2, 7, 4, 1, 6, 2], dtype=float).reshape(2, 4, order="F")
    y42 = np.array(
        [
            6, 6, 5, 5, 8, 5, 1, 7, 10, 4, 6, 7, 6, 3, 3, 7, 7, 1, 0, 0, 2, 1, 1, 0, 1, 2, 2, 3,
            0, 5, 0, 1, 3, 1, 5, 6, 1, 3, 0, 10,
        ],
        dtype=float,
    ).reshape(10, 4, order="F")
    y_one = np.array([2, 5, 1, 4, 0, 3, 6, 2, 8], dtype=float).reshape(3, 3, order="F")
    y_three = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], dtype=float).reshape(3, 4, order="F")
    parts = [
        collect(fit_nbp(y_small, group=[1, 1, 2, 2], lib_size=[100] * 4)),
        collect(fit_nbp(y42, group=[1, 1, 2, 2], lib_size=[50000] * 4)),
        collect(fit_nbp(y_one, lib_size=[20, 25, 30])),
        collect(fit_nbp(y_three, group=[1, 2, 3, 1], lib_size=[50] * 4, maxit=25)),
    ]
    return np.concatenate(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
