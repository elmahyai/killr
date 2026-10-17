import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/ggplot2")
from ggplot2.resolution import resolution

eps = sys.float_info.epsilon
x = [1.0, 1.0 + 1000 * eps, 2.0]

def one():
    return resolution(x)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
