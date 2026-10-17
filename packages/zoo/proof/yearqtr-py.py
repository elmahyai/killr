import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.yearqtr import yearqtr


def one():
    return yearqtr(2000 + np.arange(8) / 4).value


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
