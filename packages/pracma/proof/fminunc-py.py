import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/pracma")
from pracma._util import PracmaError
from pracma.opt_metric import *


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
    return np.concatenate([np.ravel(fminunc(np.array([0.0, 0.0]), lambda x: (x[0] - 1)**2 + (x[1] - 2)**2)['par']), [fminunc(np.array([0.0, 0.0]), lambda x: (x[0] - 1)**2 + (x[1] - 2)**2)['value']]])


value = flat(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    try:
        one()
    except PracmaError:
        pass
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
