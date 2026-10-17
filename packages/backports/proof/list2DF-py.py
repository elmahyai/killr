
import json
import math
import os
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/backports")
from backports import *
from backports._values import NA

def flat(x):
    if x is None:
        return "null"
    if x is NA or (isinstance(x, float) and math.isnan(x)):
        return "NA"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (list, tuple)):
        return "|".join(flat(item) for item in x)
    if isinstance(x, float):
        if math.isfinite(x) and x.is_integer():
            return str(int(x))
        return format(x, ".10g")
    return str(x)


def one():
    frame = list2DF({"x": [1, 2, 3], "y": [2, 3, 4]})
    return [",".join(str(item) for item in frame.columns["x"]), ",".join(str(item) for item in frame.columns["y"])]
value = one()
if not isinstance(value, str):
    value = flat(value)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
