import importlib
import json
import statistics
import sys
import time

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/class",
    "/home/ahmed/killr_projects/killr/packages/boot",
]
from boot.rng import set_seed
pkg = importlib.import_module("class")


def col(rows):
    return [value for column in zip(*rows) for value in column]

def one():
    book = {"x": [[0,0],[5,5]], "cl": [1,2]}
    return [int(label) for label in pkg.lvqtest(book, [[0.1,0.1],[5.1,5.1]])]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
