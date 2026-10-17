import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
from urca.unitroot_table import unitrootTable


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    parts = [
        unitrootTable(trend="nc"),
        unitrootTable(trend="c", statistic="n"),
        unitrootTable(trend="ct"),
        unitrootTable(trend="ctt", statistic="n"),
    ]
    return np.concatenate([np.ravel(part, order="F") for part in parts]).tolist()


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
