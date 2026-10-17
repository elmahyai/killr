import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.na import na_locf
from zoo.series import Zoo

NA = np.array(np.uint64(0x7FF00000000007A2)).view(np.float64)[()]


def series():
    return np.array([1.0, NA, 3.0, NA, NA], dtype=np.float64)


def as_text(value):
    array = np.asarray(value, dtype=float).reshape(-1)
    parts = []
    for number in array:
        if math.isnan(float(number)):
            bits = int(np.float64(number).view(np.uint64))
            parts.append("NA" if (bits & 0xFFFFFFFF) == 1954 else "NaN")
        else:
            parts.append(format(float(number), ".16g"))
    return "|".join(parts)


def one():
    return na_locf(series())


value = as_text(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
