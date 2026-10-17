import json
import os
import statistics
import tempfile
import time
from withr import *
def one():
    with local_par({"col": "red"}):
        inside = par("col")
    return [inside, par("col")]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
