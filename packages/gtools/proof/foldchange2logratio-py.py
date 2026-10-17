import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.foldchange import foldchange
from gtools.foldchange2logratio import foldchange2logratio
from gtools.logratio2foldchange import logratio2foldchange


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
    a = np.arange(1, 22)
    b = np.arange(21, 0, -1)
    f = foldchange(a, b)
    doc = logratio2foldchange(foldchange2logratio(f))
    edge = foldchange2logratio(
        np.array([-2.0, -1.0, 0.0, 0.5, 1.0, 2.0, np.nan, -np.inf, np.inf])
    )
    above = foldchange2logratio(np.array([2.0, 4.0, 8.0]))
    below = foldchange2logratio(np.array([-2.0, -4.0, -8.0]))
    mat = foldchange2logratio(np.array([-2.0, 0.5, 1.0, 2.0]).reshape(2, 2, order="F"))
    recycle = foldchange2logratio(np.array([2.0, 4.0, 8.0]), base=np.array([2.0, 2.0, 10.0]))
    ints = foldchange2logratio(
        np.array([2, np.int32(-2147483648), -2], dtype=np.int32),
        base=np.array([2, 2, 2], dtype=np.int32),
    )
    return np.concatenate(
        [
            np.asarray(foldchange2logratio(f), dtype=np.float64).reshape(-1),
            np.asarray(doc, dtype=np.float64).reshape(-1),
            np.asarray(edge, dtype=np.float64).reshape(-1),
            np.asarray(above, dtype=np.float64).reshape(-1),
            np.asarray(below, dtype=np.float64).reshape(-1),
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
