import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/pracma")
from pracma._util import PracmaError
from pracma.opt_program import *


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
    return np.concatenate([np.ravel(linprog(1, np.array([[1.0], [-1.0]]), [2, 0])['x']), [linprog(1, np.array([[1.0], [-1.0]]), [2, 0])['fval']]])


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
