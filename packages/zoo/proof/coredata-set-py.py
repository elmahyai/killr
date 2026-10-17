import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.series import Zoo
from zoo.coredata import coredata, coredata_set


def one():
    matrix = np.array([1, 2, 3, 4, 5, 6], dtype=float).reshape((3, 2), order="F")
    updated = coredata_set(Zoo(matrix, [1, 2, 3]), np.array([11, 12, 13, 14, 15, 16], dtype=float).reshape((3, 2), order="F"))
    vector = coredata_set(Zoo(np.array([1.0, 2, 3, 4]), [10, 11, 12, 13]), [5, 6, 7, 8])
    return list(np.ravel(coredata(updated), order="F")) + list(np.ravel(coredata(vector), order="F"))


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
