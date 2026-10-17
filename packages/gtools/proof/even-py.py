import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.even import _NA_LOGICAL, even


def fmt(v):
    if isinstance(v, (np.integer, int)) and int(v) == int(_NA_LOGICAL):
        return "NA"
    if v is True or v is False or isinstance(v, (bool, np.bool_)):
        return "TRUE" if bool(v) else "FALSE"
    item = np.asarray(v).reshape(()).item()
    if isinstance(item, (np.integer, int)) and int(item) == int(_NA_LOGICAL):
        return "NA"
    return "TRUE" if bool(item) else "FALSE"


def flat(x):
    arr = np.asarray(x, dtype=np.int8).ravel(order="F")
    return [fmt(item) for item in arr]


def one():
    parts = []
    parts.extend(flat(even(4)))
    parts.extend(flat(even(np.arange(1, 11, dtype=np.int32))))
    parts.extend(flat(even(np.arange(1, 11, dtype=np.float64) + 0.5)))
    parts.extend(flat(even(np.array([-4, -3, -2, -1, 0, 1, 2], dtype=np.float64))))
    parts.extend(flat(even(np.array([np.inf, -np.inf, np.nan], dtype=np.float64))))
    parts.extend(flat(even(np.array([np.nan, 1.0, 2.0], dtype=np.float64))))
    parts.extend(flat(even(np.array([1, 2, 3], dtype=np.int32))))
    parts.extend(
        flat(
            even(
                np.array([1.5, 2.0, 3.0, 4.0, np.nan, 0.0, -2.0], dtype=np.float64)
            )
        )
    )
    parts.extend(flat(even(np.array([], dtype=np.int32))))
    parts.extend(flat(even(np.array([True, False]))))
    return parts


even(4)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": "|".join(value), "median_ms": statistics.median(elapsed)}))
