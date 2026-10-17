import json
import statistics
import sys
import time

import numpy as np

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/boot",
    "/home/ahmed/killr_projects/killr/crates/cmeans",
]
from boot.rng import set_seed
from e1071.cmeans import cmeans


def one():
    set_seed(4242)
    x = np.array(
        [[0, 0], [3, 0], [0, 4], [6, 6], [1, 2], [5, 5]],
        dtype=float,
    )
    centers = np.array([[0, 0], [5, 5], [3, 4]], dtype=float)
    fit = cmeans(x, centers, iter_max=50, m=2, dist="euclidean", method="cmeans")
    return list(np.asarray(fit["membership"], dtype=float).reshape(-1, order="F")) + list(
        np.asarray(fit["centers"], dtype=float).reshape(-1, order="F")
    ) + list(np.asarray(fit["cluster"], dtype=float)) + list(
        np.asarray(fit["size"], dtype=float)
    ) + [float(fit["iter"]), float(fit["withinerror"])]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
