import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.make_groups import make_groups

uniform = [0.1, 0.2, 0.3]
exponential = [1.0, 2.0]
normal = [-1.0, 0.0, 1.0, 2.0]
labels = ["uniform", "exponential", "normal"]


def one():
    g = make_groups(uniform=uniform, exponential=exponential, normal=normal)
    which = [labels.index(name) + 1 for name in g["which"]]
    return [float(value) for value in g["data"]] + which


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
