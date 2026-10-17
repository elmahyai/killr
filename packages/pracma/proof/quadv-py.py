import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/pracma")
from pracma.quad_adapt import *


def flat(value):
    array = np.real(np.asarray(value, dtype=float)).reshape(-1)
    if array.size == 0:
        return ""
    parts = []
    for item in array:
        number = float(item)
        parts.append("NA" if math.isnan(number) else format(number, ".16g"))
    return "|".join(parts)


def one():
    return (lambda d: np.concatenate([d['Q'], np.array([d['fcnt'], d['estim.prec']])]))(quadv(lambda t: np.array([np.sin(t), np.cos(t)]), 0, math.pi))


value = flat(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
