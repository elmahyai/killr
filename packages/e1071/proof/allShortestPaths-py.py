import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/e1071"]
from e1071 import *


def one():
    sp = all_shortest_paths([[0, 1, 4], [None, 0, 2], [3, None, 0]])
    length = [sp["length"][r][c] if sp["length"][r][c] is not None else float("nan") for c in range(3) for r in range(3)]
    middle = [sp["middle_points"][r][c] for c in range(3) for r in range(3)]
    return length + middle

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
