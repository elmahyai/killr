import statistics
import time

from base64enc.dataURI import dataURI

x = bytes(range(1, 11))
dataURI(x)
elapsed = []
result = None
for _ in range(20):
    t0 = time.perf_counter()
    result = dataURI(x)
    elapsed.append(time.perf_counter() - t0)
med = statistics.median(elapsed)
print(f"py_ms {med * 1000:.17g}")
print(result)
