import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.pinvgauss import pinvgauss


def one():
    qs = np.array([0.2, 1, 2.5, 10, np.nan, -1, 0, np.inf, np.nan], dtype=float)
    mus = np.array([1, 1.5, 2, 0.5, 1, 1, 0, np.inf, 1], dtype=float)
    phis = np.array([0.3, 0.7, 1, 2, 0.5, 1, 1, 1, 0], dtype=float)
    return np.concatenate(
        [
            np.asarray(pinvgauss(qs, mean=mus, dispersion=phis), dtype=float).reshape(-1),
            np.asarray(
                pinvgauss(qs, mean=mus, dispersion=phis, log_p=True), dtype=float
            ).reshape(-1),
            np.asarray([pinvgauss(1.2, mean=2, shape=4)], dtype=float),
            np.asarray(
                pinvgauss([0.5, 1.5], mean=1, dispersion=[0.2, 0.8]), dtype=float
            ).reshape(-1),
            np.asarray(
                pinvgauss(
                    [0.5, 1.5], mean=1, dispersion=[0.2, 0.8], lower_tail=False
                ),
                dtype=float,
            ).reshape(-1),
            np.asarray(
                [pinvgauss(2e6, mean=1, dispersion=0.001, lower_tail=False)], dtype=float
            ),
            np.asarray([pinvgauss(0.5, mean=1, dispersion=1e-15)], dtype=float),
            np.asarray(
                pinvgauss(np.array([[0.8], [1.2]]), mean=1, dispersion=0.5), dtype=float
            ).reshape(-1),
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
