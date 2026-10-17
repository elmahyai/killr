import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.zoo_class import *
import time


def flat(value):
    if isinstance(value, (bool, np.bool_)):
        return "1" if bool(value) else "0"
    if is_zoo(value):
        return flat(value.data)
    array = np.asarray(value, dtype=float).ravel(order="F")
    if array.size == 0:
        return ""
    parts = []
    for number in array:
        parts.append("NA" if math.isnan(float(number)) else format(float(number), ".16g"))
    return "|".join(parts)


def emit(value):
    if is_zoo(value):
        return flat(value.data), flat(value.index)
    return flat(value), ""
def one():
    return xtfrm_zoo(zoo([1, float('nan'), 3], [1, 2, 3]))

value, index = emit(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "index": index, "median_ms": statistics.median(elapsed)}))
