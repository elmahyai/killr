import json
import statistics
import time

from jquerylib.jquery_core import jquery_core


result = jquery_core()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    result = jquery_core()
    elapsed.append(time.perf_counter() - t0)
print(f"py_ms {statistics.median(elapsed) * 1000:.17g}")
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
