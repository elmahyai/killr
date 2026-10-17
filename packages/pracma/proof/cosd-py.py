import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/pracma")
from pracma import *


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
        return format(value, ".16g")

    if array.ndim == 2:
        data = [fmt(v) for v in array.reshape(-1, order="F")]
        return "|".join([str(int(array.shape[0])), str(int(array.shape[1])), *data])
    return "|".join(fmt(v) for v in array.reshape(-1))


def one():
    return cosd([0, 60, 90])


value = flat(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
