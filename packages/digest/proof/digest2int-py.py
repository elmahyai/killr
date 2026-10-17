import statistics
import time

from digest.digest2int import digest2int

x = "The quick brown fox jumps over the lazy dog"
digest2int(x, 0)
elapsed = []
result = None
for _ in range(20):
    t0 = time.perf_counter()
    result = digest2int(x, 0)
    elapsed.append(time.perf_counter() - t0)
med = statistics.median(elapsed)
print(f"py_ms {med * 1000:.17g}")
print(f"result {result[0]}")
