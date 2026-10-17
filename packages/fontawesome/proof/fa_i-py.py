import statistics
import time
from fontawesome.fa_i import fa_i

fa_i("r-project")
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    result = fa_i("r-project")
    elapsed.append(time.perf_counter() - t0)
print(f"py_ms {statistics.median(elapsed) * 1000:.17g}")
print(result)
