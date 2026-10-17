import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/pracma")
from pracma.special_ellip import *


def flatten(value):
    if isinstance(value, dict):
        parts = [flatten(item) for item in value.values()]
        return np.concatenate(parts) if parts else np.array([])
    array = np.asarray(value)
    if array.ndim == 2:
        return np.real(array.reshape(-1, order="F")).astype(float)
    return np.real(array.reshape(-1)).astype(float)


def flat(value):
    array = flatten(value)
    if array.size == 0:
        return ""
    parts = []
    for item in array:
        number = float(item)
        parts.append("NA" if math.isnan(number) else format(number, ".16g"))
    return "|".join(parts)


def one():
    return ellipj([0.3, 0.8], 0.4)


value = flat(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
