import json
import os
import statistics
import tempfile
import time
from withr import *
def one():
    try:
        with_xfig("unused.fig", lambda: 2)
    except Exception as exc:
        return str(exc)
    return ""
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
