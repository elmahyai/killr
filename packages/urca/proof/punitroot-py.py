import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
from urca.punitroot import punitroot


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
        punitroot(1.2836, trend="nc", statistic="t"),
        punitroot(1.2836, n=100, trend="nc", statistic="n"),
        punitroot([1.2836, -2.5, 0.0], trend="c", statistic="t"),
        punitroot(-3.1, n=250, trend="ct", statistic="t"),
        punitroot(-1.95, n=50, trend="ctt", statistic="n"),
    ]
    return np.concatenate([np.ravel(part) for part in parts]).tolist()


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
