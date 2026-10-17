import statistics
import time
from fontawesome.fa import fa

fa("r-project", fill="red", title="R")
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    result = fa("r-project", fill="red", title="R")
    elapsed.append(time.perf_counter() - t0)
print(f"py_ms {statistics.median(elapsed) * 1000:.17g}")
print(result)
