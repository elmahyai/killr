import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.lattice_get_option import lattice_get_option


def one():
    lw = lattice_get_option("layout.widths")
    return [lw["left.padding"]["x"], lw["panel"]["x"], lw["between"]["x"]]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
