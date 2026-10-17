import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.foldchange import foldchange


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
    doc = foldchange(np.arange(1, 22), np.arange(21, 0, -1))
    edge = foldchange([1, 2, np.nan, 0, 0], [2, 1, 1, 0, 1])
    mat = foldchange(np.array([[1, 3], [2, 4]]), np.array([[4, 2], [3, 1]]))
    recycle = foldchange([1, 2, 3, 4, 5], 3)
    ints = foldchange(
        np.array([1, np.int32(-2147483648), 3], dtype=np.int32),
        np.array([2, 1, 3], dtype=np.int32),
    )
    return np.concatenate(
        [
            np.asarray(doc, dtype=np.float64).reshape(-1),
            np.asarray(edge, dtype=np.float64).reshape(-1),
            np.asarray(mat, dtype=np.float64).ravel(order="F"),
            np.asarray(recycle, dtype=np.float64).reshape(-1),
            np.asarray(ints, dtype=np.float64).reshape(-1),
        ]
    )


value = flat(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
