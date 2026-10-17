import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.gauss_quad_prob import gauss_quad_prob


def collect(result):
    return np.concatenate(
        [np.asarray(result["nodes"], dtype=float), np.asarray(result["weights"], dtype=float)]
    )


def one():
    normal = gauss_quad_prob(10, "normal")
    gamma_out = gauss_quad_prob(32, "gamma", alpha=5)
    parts = [
        np.array([float(np.sum(normal["weights"] * normal["nodes"] ** 4))], dtype=float),
        np.array([float(np.sum(gamma_out["weights"] * np.log(gamma_out["nodes"])))], dtype=float),
        collect(gauss_quad_prob(5, "uniform", l=0.2, u=1.8)),
        collect(gauss_quad_prob(5, "beta1")),
        collect(gauss_quad_prob(5, "beta2")),
        collect(gauss_quad_prob(5, "beta", alpha=3, beta=2)),
        collect(gauss_quad_prob(5, "beta", alpha=0.5, beta=0.5)),
        collect(gauss_quad_prob(5, "beta", alpha=1.5, beta=1.5)),
        collect(gauss_quad_prob(5, "normal", mu=2, sigma=3)),
        collect(gauss_quad_prob(5, "gamma", alpha=2, beta=0.5)),
        np.array([len(gauss_quad_prob(0)["nodes"])], dtype=float),
        collect(gauss_quad_prob(1, "uniform", l=1, u=5)),
        collect(gauss_quad_prob(1, "normal", mu=7)),
        collect(gauss_quad_prob(1, "gamma", alpha=3, beta=2)),
        collect(gauss_quad_prob(1, "beta", alpha=2, beta=3)),
        collect(gauss_quad_prob(2.9)),
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
