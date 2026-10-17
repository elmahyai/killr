import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/randomForest"]
from randomForest import margin, na_roughfix, outlier

def one():
    return margin([[0.7, 0.3], [0.2, 0.8], [0.4, 0.6]], ["a", "b", "a"])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
