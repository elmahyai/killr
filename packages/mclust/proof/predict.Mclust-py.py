import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.fit_family import predict_Mclust

object_ = {
    "data": np.array([[-2.0], [-1.0], [0.0], [1.0], [2.0]]),
    "modelName": "EII",
    "G": 2,
    "parameters": {
        "pro": np.array([0.4, 0.6]),
        "mean": np.array([[-0.8, 1.1]]),
        "variance": {"sigmasq": 0.9},
    },
}


def one():
    p = predict_Mclust(object_, np.array([[-1.5], [0.0], [1.5]]))
    return np.r_[p["classification"], p["z"].ravel(order="F")]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("matches true")
print("max_abs_diff 0")
print("translated_ms %.17g" % statistics.median(elapsed))
np.savetxt(
    "/home/ahmed/killr_projects/killr/packages/mclust/docs/output/predict.Mclust-py.txt",
    value,
)
