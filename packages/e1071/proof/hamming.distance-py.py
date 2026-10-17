import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/e1071"]
from e1071 import *


def one():
    matrix = hamming_distance([[1, 0, 1], [1, 1, 0], [0, 0, 1]])
    flat = [matrix[r][c] for c in range(3) for r in range(3)]
    return [hamming_distance([1, 0, 1], [1, 1, 0]), *flat]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
