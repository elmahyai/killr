import json
import statistics
import time
from fansi import has_sgr

def one():
    return has_sgr(["hello\x1b[31mworld\x1b[m", "\n", "hello world"], warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
