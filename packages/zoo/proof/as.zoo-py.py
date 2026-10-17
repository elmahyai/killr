import json
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.as_zoo import DataFrame, Ts, as_zoo, factor
from zoo.zooreg import zooreg


def one():
    x = as_zoo([2, 4, 6])
    m = as_zoo(np.arange(1, 7, dtype=np.int32).reshape((3, 2), order="F"))
    d = as_zoo(DataFrame(a=[1, 2], b=[1.5, 3]))
    f = as_zoo(factor(["b", "a", "b"], levels=["a", "b", "c"]))
    tser = as_zoo(Ts(np.arange(1, 11), start=(1959, 2), frequency=4))
    q = as_zoo(np.arange(1, 5), frequency=4)
    big = as_zoo(np.arange(1, 100001, dtype=np.int32))
    dropped = as_zoo(zooreg(np.arange(1, 5), frequency=4, calendar=False))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            as_zoo(
                np.arange(1, 4, dtype=np.int32).reshape((3, 1), order="F"),
                order_by=np.array([1, 2, 4], dtype=np.int32),
                frequency=2.5,
            )
            bad = 0.0
        except ValueError as exc:
            bad = 1.0 if str(exc) == "missing value where TRUE/FALSE needed" else 0.0
        del caught
    parts = [
        np.asarray(x.data, dtype=float).reshape(-1),
        np.asarray(x.index, dtype=float).reshape(-1),
        np.asarray(m.data, dtype=float).reshape(-1, order="F"),
        np.asarray(d.data, dtype=float).reshape(-1, order="F"),
        np.asarray(f.data, dtype=float).reshape(-1),
        np.asarray(tser.index, dtype=float).reshape(-1),
        [tser.frequency],
        np.asarray(q.index, dtype=float).reshape(-1),
        [q.frequency],
        [float(np.sum(np.asarray(big.data, dtype=np.float64)))],
        [0.0 if dropped.frequency is None else 1.0],
        [1.0 if dropped.regular else 0.0],
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
