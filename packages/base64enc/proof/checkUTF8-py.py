import statistics
import time

from base64enc.checkUTF8 import checkUTF8

x = ("Hello, 世界\n" * 10000).encode("utf-8")
checkUTF8(x)
elapsed = []
result = None
for _ in range(20):
    t0 = time.perf_counter()
    result = checkUTF8(x)
    elapsed.append(time.perf_counter() - t0)
med = statistics.median(elapsed)
print(f"py_ms {med * 1000:.17g}")
print(result)
