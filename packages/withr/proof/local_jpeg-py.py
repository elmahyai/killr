import json
import os
import statistics
import tempfile
import time
from withr import *
def one():
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    with local_jpeg(path, width=200, height=200):
        pass
    ok = os.path.getsize(path) > 0
    os.remove(path)
    return int(ok)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
