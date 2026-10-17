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
    set_seed(1)
    rows = [[0,0],[0,1],[0.2,0.1],[5,5],[5,6],[5.2,4.8]]
    init = [[0,0],[1,0],[0,1],[1,1]]
    return col(pkg.SOM(rows, pkg.somgrid(2, 2), alpha=[0.5, 0.1], radii=[2, 1], init=init)["codes"])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
