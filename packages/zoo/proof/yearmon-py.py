import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.yearmon import yearmon


def one():
    return yearmon(2000 + np.arange(12) / 12).value


def payload(values):
    out = []
    for value in values:
        if value != value:
            out.append(None)
        else:
            out.append(float(value))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": payload(value), "median_ms": statistics.median(elapsed)}))
