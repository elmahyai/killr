import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/e1071"]
from e1071 import *


def one():
    drawn = rdiscrete(20, [0.2, 0.5, 0.3], [1, 2, 3])
    ok = len(drawn) == 20 and all(value in (1, 2, 3) for value in drawn)
    return [len(drawn), 1 if ok else 0]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
