import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.order import ORDER_default


def one():
    return (
        ORDER_default([2, None, 1], na_last=None)
        + ORDER_default([1, 1, 2], [2, 1, 0], decreasing=True)
        + ORDER_default([-1, -3, 2, 0])
        + ORDER_default([0.0, -0.0, 1.0])
        + ORDER_default([1, float("nan"), None, 0, -0.0, -1])
    )


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
