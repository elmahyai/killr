import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.yearmon import as_yearmon


def one():
    return as_yearmon(["Mar 2007", "January 2000", "December 1999"]).value


def payload(values):
    out = []
    for value in values:
        if value != value:
            out.append(None)
        else:
            out.append(float(value))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": payload(value), "median_ms": statistics.median(elapsed)}))
