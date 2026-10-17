import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
from boot.rng import set_seed
from gtools.quantcut import quantcut
from mass._r_rng import norm_rand


def flat(factor):
    return [label if label is not None else "NA" for label in factor.labels]


def one():
    set_seed(1234)
    x = np.array([norm_rand() for _ in range(1000)], dtype=np.float64)
    quartiles = flat(quantcut(x))
    deciles1 = flat(quantcut(x, 10))
    deciles2 = flat(quantcut(x, np.arange(0.0, 1.1, 0.1)))
    if deciles1 != deciles2:
        raise RuntimeError("deciles mismatch")
    x2 = np.round(x)
    tied = flat(quantcut(x2, 10))
    x3 = [1.0, 2.0, 3.0, float("nan"), 5.0]
    small = flat(quantcut(x3, 2))
    return quartiles + deciles1 + tied + small


quantcut(np.array([1.0, 2.0]))
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": "|".join(value), "median_ms": statistics.median(elapsed)}))
