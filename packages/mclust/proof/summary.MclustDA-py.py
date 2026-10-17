import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.summary_mclust_da import summary_mclust_da


def make_mclust_da():
    x = np.array([[-1, -1], [0, 0], [2, 2], [3, 3]], dtype=float)

    def make_model(mean, s):
        return {
            "n": 2,
            "d": 2,
            "G": 1,
            "modelName": "EII",
            "parameters": {
                "pro": 1.0,
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
        "models": {"A": make_model([0, 0], 1), "B": make_model([3, 3], 2)},
        "type": "EDDA",
        "n": 4,
        "d": 2,
        "prop": {"A": 0.5, "B": 0.5},
        "data": x,
        "class": np.array(["A", "A", "B", "B"], dtype=object),
        "loglik": -12.5,
        "df": 8,
        "bic": 1.25,
    }


def one():
    return summary_mclust_da(make_mclust_da())


value = one()
print(value["type"])
print(",".join(map(str, value["n"])))
print(",".join(value["classes"]))
print(",".join(map(str, value["G"])))
print(",".join(value["modelName"]))
print("%.17g %.17g" % (value["ce"], value["brier"]))
print(",".join(map(str, value["tab"]["values"].ravel())))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
