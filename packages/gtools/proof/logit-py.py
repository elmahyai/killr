import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.logit import logit


def flat(x):
    if x is None:
        return "null"
    array = np.asarray(x)
    if array.size == 0:
        return ""

    def fmt(v):
        value = float(np.real(v))
        if math.isnan(value):
            return "NA"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        return format(value, ".16g")

    if array.ndim == 2:
        data = [fmt(v) for v in array.reshape(-1, order="F")]
        return "|".join([str(int(array.shape[0])), str(int(array.shape[1])), *data])
    return "|".join(fmt(v) for v in array.reshape(-1))


def one():
    x = np.arange(41, dtype=np.float64) / 4.0
    xt = logit(x, min=0, max=10)
    eps = float(np.finfo(np.float64).eps)
    close = logit(np.array([1e-16, 1.0 - 1e-16, eps, 1.0 - eps, 0.5]))
    mat = logit(np.array([[0.2, 0.4], [0.8, 0.6]]), min=np.array([0.0, 0.1]), max=1)
    recycled = logit([0.2, 0.4, 0.6, 0.8], min=[0.0, 0.1], max=1)
    return np.concatenate(
        [
            np.asarray(xt, dtype=np.float64).reshape(-1),
            np.asarray(close, dtype=np.float64).reshape(-1),
            np.asarray(mat, dtype=np.float64).ravel(order="F"),
            np.asarray(recycled, dtype=np.float64).reshape(-1),
        ]
    )


value = flat(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
