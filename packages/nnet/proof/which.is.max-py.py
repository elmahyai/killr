import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/nnet"]
from nnet import class_ind, which_is_max

def one():
    return [which_is_max([1, 4, 2])]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
