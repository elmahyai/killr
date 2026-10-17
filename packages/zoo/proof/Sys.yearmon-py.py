import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.yearmon import sys_yearmon, yearmon

current = sys_yearmon()
if current.r_class != "yearmon" or len(current) != 1:
    raise SystemExit("Sys.yearmon did not return a yearmon")

def one():
    return yearmon(2000 + (3 - 1) / 12).value


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(value[0])], "median_ms": statistics.median(elapsed)}))
