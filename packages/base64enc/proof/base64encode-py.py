import statistics
import time

from base64enc.base64encode import base64encode

x = list(range(1, 101))
base64encode(x, 70)
elapsed = []
result = None
for _ in range(20):
    t0 = time.perf_counter()
    result = base64encode(x, 70)
    elapsed.append(time.perf_counter() - t0)
med = statistics.median(elapsed)
print(f"py_ms {med * 1000:.17g}")
print("\n".join(result))
