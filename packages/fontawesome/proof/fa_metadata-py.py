import json
import statistics
import time
from fontawesome.fa_metadata import fa_metadata

fa_metadata()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    result = fa_metadata()
    elapsed.append(time.perf_counter() - t0)
print(f"py_ms {statistics.median(elapsed) * 1000:.17g}")
print(json.dumps(result, separators=(",", ":")))
