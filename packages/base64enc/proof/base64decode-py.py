import statistics
import time

from base64enc.base64decode import base64decode
from base64enc.base64encode import base64encode

enc = base64encode(list(range(1, 101)), 70)
base64decode(enc)
elapsed = []
result = None
for _ in range(20):
    t0 = time.perf_counter()
    result = base64decode(enc)
    elapsed.append(time.perf_counter() - t0)
med = statistics.median(elapsed)
print(f"py_ms {med * 1000:.17g}")
print(" ".join(str(b) for b in result))
