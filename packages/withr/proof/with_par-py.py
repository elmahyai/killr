import json
import os
import statistics
import tempfile
import time
from withr import *
def one():
    old = par("col")
    inside = with_par({"col": "red", "pch": 19}, lambda: par("col"))
    return [inside, par("col"), old]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
