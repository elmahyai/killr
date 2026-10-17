import json
import statistics
import sys
import time

import numpy as np

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/crates/svm",
]
from boot.rng import set_seed
from e1071.svm import svm


def one():
    set_seed(4242)
    x = np.array(
        [
            [0.0, 1.0],
            [1.2, 0.8],
            [2.5, 2.7],
            [2.8, 2.4],
            [0.1, 0.9],
            [2.6, 2.5],
        ],
        dtype=float,
    )
    y = ["setosa", "setosa", "versicolor", "versicolor", "setosa", "versicolor"]
    fit = svm(
        x,
        y,
        scale=True,
        kernel="radial",
        cost=1,
        gamma=0.5,
        probability=False,
        cross=0,
    )
    fitted = fit["fitted"]
    if fitted.dtype == object:
        level_index = {level: index + 1 for index, level in enumerate(fit["levels"])}
        fitted_num = [float(level_index[v]) for v in fitted]
    else:
        fitted_num = list(np.asarray(fitted, dtype=float))
    return (
        [float(fit["tot.nSV"])]
        + list(np.asarray(fit["index"], dtype=float))
        + list(np.asarray(fit["rho"], dtype=float))
        + list(np.asarray(fit["coefs"], dtype=float).reshape(-1, order="F"))
        + list(np.asarray(fit["SV"], dtype=float).reshape(-1, order="F"))
        + fitted_num
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
