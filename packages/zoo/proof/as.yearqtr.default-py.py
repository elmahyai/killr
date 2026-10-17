import json
import statistics
import sys
import time
import warnings

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.yearqtr import as_yearqtr_default


def one():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return as_yearqtr_default(["2001.5", "2001 Q2", "2001.2"]).value


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
