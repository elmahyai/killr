import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.as_date import as_date
from zoo.zooreg import zooreg


def one():
    q = zooreg(np.arange(1, 5), start=(1959, 2), frequency=4)
    nocal = zooreg(np.arange(1, 5), frequency=4, start=1, calendar=False)
    mon = zooreg(np.arange(1, 5), start=2000, frequency=12)
    both = zooreg(np.arange(1, 5), frequency=4, deltat=1)
    near = zooreg(np.arange(1, 4), frequency=4 + 1e-7)
    daily = zooreg(np.arange(1, 4), start=as_date("2000-01-01"), frequency=1)
    ints = zooreg([1.2, 2.8], start=np.int32(5), frequency=1)
    empty = zooreg()
    big = zooreg(np.arange(1, 20001), frequency=4, calendar=False)
    try:
        zooreg(np.arange(1, 4), start=5, end=1)
        bad = 0.0
    except ValueError as exc:
        bad = 1.0 if str(exc) == "start cannot be after end" else 0.0
    na = int(np.asarray(empty.data).reshape(-1)[0]) == -128 and empty.data.r_mode == "logical"
    parts = [
        np.asarray(q.index, dtype=float).reshape(-1),
        [q.frequency],
        np.asarray(nocal.index, dtype=float).reshape(-1),
        np.asarray(mon.index, dtype=float).reshape(-1),
        [mon.frequency],
        np.asarray(both.index, dtype=float).reshape(-1),
        np.asarray(near.index, dtype=float).reshape(-1),
        [near.frequency],
        np.asarray(daily.index, dtype=float).reshape(-1),
        np.asarray(ints.data, dtype=float).reshape(-1),
        np.asarray(ints.index, dtype=float).reshape(-1),
        [1.0 if np.asarray(ints.index).dtype == np.int32 else 0.0],
        [1.0 if na else 0.0],
        np.asarray(empty.index, dtype=float).reshape(-1),
        [empty.frequency],
        [float(np.sum(np.asarray(big.index, dtype=np.float64)))],
        [bad],
    ]
    return np.concatenate([np.asarray(p, dtype=float).reshape(-1) for p in parts])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
