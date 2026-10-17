import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.estep_eei import estepEEI

X = np.column_stack(
    [
        [0.1, 1.2, -0.4, 2.9, 3.3, 2.2, 0.7, 4.1],
        [1.5, 3.8, -1.0, 2.0, 0.3, 2.7, 1.9, 3.1],
    ]
)
MU = np.array([[0.5, 3.0], [0.2, 2.5]])
pars = {"pro": np.array([0.4, 0.6]), "mean": MU, "variance": {"modelName": "EEI", "scale": 0.8, "shape": np.array([1.0, 2.0])}}
pars_noise = {"pro": np.array([0.3, 0.5, 0.2]), "mean": MU, "variance": {"modelName": "EEI", "scale": 0.8, "shape": np.array([1.0, 2.0])}}


def emit(res):
    return [res["loglik"], res["returnCode"]] + np.asarray(res["z"]).ravel(order="F").tolist()


def one():
    return [estepEEI(X, pars), estepEEI(X, pars_noise)]


value = one()
for v in emit(value[0]) + emit(value[1]):
    print("%.17g" % v)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
