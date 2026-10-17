import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.expected_deviance import expected_deviance


def collect(ed):
    return np.concatenate(
        [np.asarray(ed["mean"], dtype=float).reshape(-1), np.asarray(ed["variance"], dtype=float).reshape(-1)]
    )


def one():
    parts = [
        collect(expected_deviance(mu=3, family="poisson")),
        collect(expected_deviance(mu=0.01, family="binomial", binom_size=10)),
        collect(expected_deviance(mu=10, family="Gamma", gamma_shape=5)),
        collect(expected_deviance(mu=10, family="negative.binomial", nbinom_size=5)),
        collect(expected_deviance(mu=np.array([0.5, 2, 7], dtype=float), family="gaussian")),
        collect(expected_deviance(mu=np.array([0, 1.5, 4], dtype=float), family="inverse.gaussian")),
        collect(
            expected_deviance(
                mu=np.exp(np.linspace(np.log(0.01), np.log(50), 30)),
                family="poisson",
            )
        ),
        collect(
            expected_deviance(
                mu=np.linspace(0.001, 0.11, 40),
                family="binomial",
                binom_size=10,
            )
        ),
        collect(
            expected_deviance(
                mu=np.array([0.2, 1, 5, 20, 100], dtype=float),
                family="negative.binomial",
                nbinom_size=np.array([0.1, 0.5, 2, 10, 50], dtype=float),
            )
        ),
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
