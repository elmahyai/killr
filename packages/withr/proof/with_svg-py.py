import json
import os
import statistics
import tempfile
import time
from withr import *
def one():
    fd, path = tempfile.mkstemp(suffix=".svg")
    os.close(fd)
    val = with_svg(path, lambda: 2, width=4, height=4)
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
