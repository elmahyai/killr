import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.core import as_factor_or_shingle


def one():
    out = as_factor_or_shingle([1.5, 2.5, 1.5, 3.0], subset=[True, False, True, True], drop=True)
    flat = list(out.data)
    for level in out.levels:
        flat.extend(level)
    return flat


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
