import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.as_date import as_date_ts
from zoo.as_zoo import Ts


def days(x):
    return np.asarray(x, dtype=float).reshape(-1)


def one():
    q = days(as_date_ts(Ts(np.arange(1, 5), start=2000, frequency=4)))
    q2 = days(as_date_ts(Ts(np.arange(1, 4), start=(2000, 2), frequency=4)))
    m = days(as_date_ts(Ts(np.arange(1, 4), start=(2000, 2), frequency=12)))
    a = days(as_date_ts(Ts(np.arange(1, 4), start=1999, frequency=1)))
    off = days(as_date_ts(Ts(np.arange(1, 4), start=(1999, 11), frequency=12), offset=1))
    big = days(as_date_ts(Ts(np.arange(1, 5001), start=2000, frequency=12)))
    try:
        as_date_ts(Ts(np.arange(1, 4), start=2000, frequency=7))
        bad = 0.0
    except ValueError as exc:
        bad = 1.0 if str(exc) == "unable to convert ts time to Date class" else 0.0
    return np.concatenate([q, q2, m, a, off, [float(np.sum(big)), bad]])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
