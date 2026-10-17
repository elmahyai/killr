import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.index2char import index2char


def one():
    labels = []
    labels += index2char([2000, 2000.25, 2000.5])
    labels += index2char([2000 + 0.25 * i for i in range(4)], frequency=4)
    labels += index2char([1999.75, 2000], frequency=4)
    labels += index2char([-1.5, -1.25, -1], frequency=4)
    labels += index2char([1 / 3, 1e-4, 1e5], digits=4)
    labels += index2char([2000, 2000.3, 2000.5], frequency=4)
    return labels


def as_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], str):
            return "|".join(value)
        parts = []
        for item in value:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                parts.append("NA")
            else:
                parts.append(format(float(item), ".16g"))
        return "|".join(parts)
    array = np.asarray(value, dtype=float).reshape(-1)
    parts = []
    for number in array:
        number = float(number)
        parts.append("NA" if math.isnan(number) else format(number, ".16g"))
    return "|".join(parts)


value = as_text(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
