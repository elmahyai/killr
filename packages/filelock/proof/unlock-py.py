
import json
import statistics
import tempfile
import time

from filelock import lock, unlock

def one():
    path = tempfile.mktemp(prefix="filelock")
    held = lock(path)
    return unlock(held)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
