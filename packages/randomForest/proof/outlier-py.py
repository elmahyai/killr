import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/randomForest"]
from randomForest import margin, na_roughfix, outlier

def one():
    return outlier([[1, 0.2, 0.8], [0.2, 1, 0.1], [0.8, 0.1, 1]])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
