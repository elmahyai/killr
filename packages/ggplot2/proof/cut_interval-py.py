import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/ggplot2")
from ggplot2.cut_interval import cut_interval

x = list(range(1, 101))

def one():
    return cut_interval(x, 10)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
codes = [None if code is None else int(code) for code in value.codes]
print(json.dumps({"value": codes, "median_ms": [statistics.median(elapsed)]}))
