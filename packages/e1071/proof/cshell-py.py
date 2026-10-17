import json
import statistics
import sys
import time

import numpy as np

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/boot",
    "/home/ahmed/killr_projects/killr/crates/cshell",
]
from boot.rng import set_seed
from e1071.cshell import cshell


def one():
    set_seed(4242)
    x = np.array(
        [[0, 0], [3, 0], [0, 4], [6, 6], [1, 2], [5, 5]],
        dtype=float,
    )
    centers = np.array([[0, 0], [5, 5], [3, 4]], dtype=float)
    fit = cshell(x, centers, iter_max=50, m=2, dist="euclidean", method="cshell")
    return list(np.asarray(fit["membership"], dtype=float).reshape(-1, order="F")) + list(
        np.asarray(fit["centers"], dtype=float).reshape(-1, order="F")
    ) + list(np.asarray(fit["radius"], dtype=float)) + list(
        np.asarray(fit["cluster"], dtype=float)
    ) + list(np.asarray(fit["size"], dtype=float)) + [
        float(fit["iter"]),
        float(fit["withinerror"]),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
