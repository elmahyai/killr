import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.series import Zoo
from zoo.window import lag_zoo


def show(values):
    array = np.asarray(values, dtype=float)
    flat = array.reshape(-1, order="F") if array.ndim == 2 else array.reshape(-1)
    parts = []
    for value in flat:
        value = float(value)
        parts.append("NA" if math.isnan(value) else format(value, ".16g"))
    return "|".join(parts)


def one():
    x = Zoo(np.array([10.0, 20.0, 30.0, 40.0]), np.array([1.0, 2.0, 3.0, 4.0]))
    z = lag_zoo(x, k=1, na_pad=True)
    return show(z.data) + ";" + show(z.index)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
