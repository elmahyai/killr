import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.loglik_mclust_da import logLik_MclustDA


def make_mclust_da():
    x = np.array([[-1, -1], [0, 0], [2, 2], [3, 3]], dtype=float)

    def make_model(mean, s):
        return {
            "n": 2,
            "d": 2,
            "G": 1,
            "modelName": "EII",
            "parameters": {
                "pro": np.array([1.0]),
                "mean": np.array(mean, dtype=float).reshape(2, 1),
                "variance": {
                    "d": 2,
                    "G": 1,
                    "sigma": np.eye(2)[:, :, None] * s,
                    "Sigma": np.eye(2) * s,
                    "sigmasq": s,
                },
            },
        }

    return {
        "models": {
            "A": make_model([0, 0], 1),
            "B": make_model([3, 3], 2),
        },
        "type": "EDDA",
        "n": 4,
        "d": 2,
        "prop": {"A": 0.5, "B": 0.5},
        "data": x,
    }


def one():
    return float(logLik_MclustDA(make_mclust_da()))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % value)
print("%.17g" % statistics.median(elapsed))
