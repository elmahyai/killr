import importlib
import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/class"]
pkg = importlib.import_module("class")

train = [[0, 0], [1, 0], [0, 3], [10, 0]]
test = [[0.1, 0.1], [9, 0.1]]
classes = ["a", "b", "a", "b"]
levels = []
for item in classes:
    if item not in levels:
        levels.append(item)


def codes(labels):
    return [levels.index(item) + 1 for item in labels]
def one():
    return codes(pkg.knn1(train, test, classes))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
