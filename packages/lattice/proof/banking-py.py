import json
import statistics
import subprocess
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.core import banking

_SUNSPOT = [
    float(value)
    for value in subprocess.check_output(
        ["Rscript", "-e", "cat(paste(as.numeric(sunspot.year), collapse=','))"],
        text=True,
    ).strip().split(",")
]


def one():
    x = list(range(1700, 1989))
    y = _SUNSPOT
    dx = [x[i] - x[i - 1] for i in range(1, len(x))]
    dy = [y[i] - y[i - 1] for i in range(1, len(y))]
    return banking(dx, dy)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
