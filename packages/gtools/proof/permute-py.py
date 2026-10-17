import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
from boot.rng import set_seed
from gtools.permute import permute


def flat(x):
    if x is None:
        return "null"
    if isinstance(x, (list, tuple)):
        parts = []
        for v in x:
            if isinstance(v, str):
                parts.append(v)
            else:
                fv = float(v)
                parts.append("NA" if np.isnan(fv) else format(fv, ".16g"))
        return "|".join(parts)
    array = np.asarray(x)
    if array.size == 0:
        return ""

    def fmt(v):
        if isinstance(v, (str, bytes)):
            return str(v)
        value = float(np.real(v))
        if np.isnan(value):
            return "NA"
        return format(value, ".16g")

    return "|".join(fmt(v) for v in array.reshape(-1))


def one():
    set_seed(1234)
    a = permute(np.arange(1, 11, dtype=np.int64))
    set_seed(5678)
    b = permute(np.arange(1, 101, dtype=np.int64))
    set_seed(9012)
    c = permute([1.5, 2.5, 3.5, 4.5, 5.5])
    set_seed(3456)
    d = permute(list("abcdefghijkl"))
    numeric = np.concatenate(
        [
            np.asarray(a, dtype=np.float64).reshape(-1),
            np.asarray(b, dtype=np.float64).reshape(-1),
            np.array([float(np.sum(b))], dtype=np.float64),
            np.asarray(c, dtype=np.float64).reshape(-1),
        ]
    )
    return list(numeric) + list(d)


permute(np.arange(1, 4, dtype=np.int64))
value = flat(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
