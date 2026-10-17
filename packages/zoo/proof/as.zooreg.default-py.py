import json
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.as_zoo import as_zooreg_default, zoo_create


def one():
    x = as_zooreg_default(np.arange(1, 6))
    y = as_zooreg_default(np.arange(1, 5), frequency=4)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        irreg = as_zooreg_default(zoo_create([1, 2, 4], order_by=[1, 2, 3.3]))
    flagged = 0.0
    if caught and "underlying regularity" in str(caught[0].message):
        flagged = 1.0
    big = as_zooreg_default(np.arange(1, 20001))
    parts = [
        np.asarray(x.data, dtype=float).reshape(-1),
        np.asarray(x.index, dtype=float).reshape(-1),
        [x.frequency],
        np.asarray(y.index, dtype=float).reshape(-1),
        [y.frequency],
        np.asarray(irreg.data, dtype=float).reshape(-1),
        np.asarray(irreg.index, dtype=float).reshape(-1),
        [irreg.frequency],
        [flagged],
        [float(np.sum(np.asarray(big.index, dtype=np.float64)))],
    ]
    return np.concatenate([np.asarray(p, dtype=float).reshape(-1) for p in parts])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
