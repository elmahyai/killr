import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.qinvgauss import qinvgauss


def one():
    ps = np.array([0.001, 0.05, 0.5, 0.95, 0.999, np.nan, -0.1, 0, 1, 1.1], dtype=float)
    mus = np.array([1, 1.5, 2, 0.5, 1, 1, 1, 1, 1, 1], dtype=float)
    phis = np.array([0.3, 0.7, 1, 2, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=float)
    ps_ok = np.array([0.001, 0.05, 0.5, 0.95, 0.999], dtype=float)
    mus_ok = np.array([1, 1.5, 2, 0.5, 1], dtype=float)
    phis_ok = np.array([0.3, 0.7, 1, 2, 0.5], dtype=float)
    return np.concatenate(
        [
            np.asarray(qinvgauss(ps, mean=mus, dispersion=phis), dtype=float).reshape(-1),
            np.asarray(
                qinvgauss(np.log(ps_ok), mean=mus_ok, dispersion=phis_ok, log_p=True),
                dtype=float,
            ).reshape(-1),
            np.asarray([qinvgauss(0.6, mean=2, shape=4)], dtype=float),
            np.asarray(
                qinvgauss([0.25, 0.75], mean=1, dispersion=[0.2, 0.8]), dtype=float
            ).reshape(-1),
            np.asarray(
                qinvgauss(
                    [0.25, 0.75], mean=1, dispersion=[0.2, 0.8], lower_tail=False
                ),
                dtype=float,
            ).reshape(-1),
            np.asarray([qinvgauss(0.99, mean=1, dispersion=1e-10)], dtype=float),
            np.asarray([qinvgauss(0.5, mean=np.inf, dispersion=0.5)], dtype=float),
            np.asarray(
                qinvgauss(np.array([[0.3], [0.7]]), mean=1, dispersion=0.5), dtype=float
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
