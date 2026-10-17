import json
import statistics
import time
from fontawesome.fa_html_dependency import fa_html_dependency

fa_html_dependency()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    result = fa_html_dependency()
    elapsed.append(time.perf_counter() - t0)
print(f"py_ms {statistics.median(elapsed) * 1000:.17g}")
print(json.dumps(result, separators=(",", ":")))
