import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.series import Zoo
from zoo.index import index, time_set


def one():
    plain = time_set(Zoo(np.arange(1, 4), [1, 2, 3]), [3, 1, 2])
    regular = time_set(
        Zoo(np.arange(1, 5), [0, 0.25, 0.5, 0.75], frequency=4, regular=True),
        [0, 0.5, 1.0, 1.5],
    )
    return list(index(plain)) + list(index(regular)) + [float(regular.frequency), 1.0 if regular.regular else 0.0]


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
