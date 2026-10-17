import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.yearqtr import as_yearqtr, format_yearqtr


def one():
    values = as_yearqtr([2000, 2001.25, 99.75, -1.5, float("nan")])
    return format_yearqtr(values, "%Y Q%q | %y | %C")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
