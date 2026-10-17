import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/pracma")
from pracma.interp_basis import *


def as_text(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)) and (not value or isinstance(value[0], str)):
        return "|".join(str(item) for item in value)
    array = np.asarray(value)
    if array.dtype.kind in "UOS":
        return "|".join(str(item) for item in array.reshape(-1))
    if array.ndim == 2:
        array = np.real(array).reshape(-1, order="F")
    else:
        array = np.real(np.asarray(array, dtype=float)).reshape(-1)
    parts = []
    for number in array:
        number = float(number)
        parts.append("NA" if math.isnan(number) else format(number, ".16g"))
    return "|".join(parts)


def one():
    return np.ravel(lagrangeInterp([0, 1, 2, 3], [0, 1, 0, 1], [0.5, 1.5]), order='F')


value = as_text(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
