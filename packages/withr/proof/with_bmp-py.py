import json
import os
import statistics
import tempfile
import time
from withr import *
def one():
    fd, path = tempfile.mkstemp(suffix=".bmp")
    os.close(fd)
    val = with_bmp(path, lambda: 2, width=200, height=200)
    ok = os.path.getsize(path) > 0
    os.remove(path)
    return [val, int(ok)]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
