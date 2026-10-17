import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.gauss_quad import gauss_quad


def collect(result):
    return np.concatenate([np.asarray(result["nodes"], dtype=float), np.asarray(result["weights"], dtype=float)])


def one():
    example = gauss_quad(10, "laguerre", alpha=5)
    mean = float(np.sum(example["weights"] * example["nodes"]) / math.gamma(6))
    parts = [
        collect(example),
        np.array([mean], dtype=float),
        collect(gauss_quad(5, "legendre")),
        collect(gauss_quad(5, "chebyshev1")),
        collect(gauss_quad(5, "chebyshev2")),
        collect(gauss_quad(5, "hermite")),
        collect(gauss_quad(5, "jacobi", alpha=5, beta=1.1)),
        collect(gauss_quad(5, "lag", alpha=5)),
        np.array([len(gauss_quad(0)["nodes"])], dtype=float),
        collect(gauss_quad(1)),
        collect(gauss_quad(1, "laguerre", alpha=5)),
        collect(gauss_quad(1, "jacobi", alpha=5, beta=1.1)),
        collect(gauss_quad(2.9)),
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
