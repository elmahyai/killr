import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/e1071"]
from e1071 import *


def one():
    scaled = scale_data_frame({"a": [1, 2, 3], "b": [True, False, True]})
    values = scaled["columns"]["a"] + scaled["columns"]["b"]
    return values + [scaled["center"]["a"], scaled["center"]["b"]]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
