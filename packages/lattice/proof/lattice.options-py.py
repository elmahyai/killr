import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.lattice_options import lattice_options


def one():
    ap = lattice_options("axis.padding")["axis.padding"]
    return [ap["numeric"], ap["factor"]]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
