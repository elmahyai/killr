import json
import statistics
import sys
import time

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/proxy",
]
from e1071 import gknn, predict_gknn

rows = [[0, 0], [3, 0], [0, 4], [6, 6]]
labels = ["a", "b", "a", "b"]
new = [[0.2, 0.2], [2.8, 0.2]]
levels = []
for item in labels:
    if item not in levels:
        levels.append(item)
def one():
    return [levels.index(item) + 1 for item in predict_gknn(gknn(rows, labels, k=1, scale=False), new)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
