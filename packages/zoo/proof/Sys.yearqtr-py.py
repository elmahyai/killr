import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.yearqtr import sys_yearqtr, yearqtr

current = sys_yearqtr()
if current.r_class != "yearqtr" or len(current) != 1:
    raise SystemExit("Sys.yearqtr did not return a yearqtr")

def one():
    return yearqtr(2000 + (1 - 1) / 4).value


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(value[0])], "median_ms": statistics.median(elapsed)}))
